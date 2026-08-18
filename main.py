from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from analyzer import run_analysis
from app_logging import configure_logging
from dashboard import build_dashboard
from db import (
    get_latest_rankings,
    get_price_history,
    get_recent_full_runs,
    get_recent_runs,
    initialize_database,
    save_analysis_result,
)
from email_report import send_scan_email_report
from file_writer import write_json
from rebalance import build_rebalance_plan, load_holdings
from reporting import build_price_history_text, build_rebalance_report_text, build_report_text
from rebalance_schedule import monthly_rebalance_due
from site_server import serve_site


def parse_args() -> argparse.Namespace:
    argv = sys.argv[1:]
    if argv and argv[0] not in {"scan", "report", "serve", "rebalance", "prices", "-h", "--help"}:
        argv = ["scan", *argv]

    parser = argparse.ArgumentParser(description="Momentum stock scanner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Run a scan and persist results")
    scan_parser.add_argument("input", help="Path to JSON stock configuration")
    scan_parser.add_argument("--output", default="results.json", help="Path to output JSON file")
    scan_parser.add_argument(
        "--db",
        default="data/stock_analyzer.db",
        help="Path to SQLite database file",
    )
    scan_parser.add_argument(
        "--log",
        default="logs/stock_analyzer.log",
        help="Path to log file",
    )
    scan_parser.add_argument(
        "--dashboard-output",
        default="site/index.html",
        help="Path to generated dashboard HTML file",
    )
    scan_parser.add_argument(
        "--email-report",
        action="store_true",
        help="Send a scan summary email using local SMTP environment variables",
    )
    scan_parser.add_argument(
        "--holdings-file",
        default="holdings.txt",
        help="Holdings file used for rebalance content in the email report",
    )

    report_parser = subparsers.add_parser("report", help="Show recent scans and latest rankings")
    report_parser.add_argument(
        "--db",
        default="data/stock_analyzer.db",
        help="Path to SQLite database file",
    )
    report_parser.add_argument(
        "--log",
        default="logs/stock_analyzer.log",
        help="Path to log file",
    )
    report_parser.add_argument("--runs", type=int, default=5, help="Number of recent runs to display")
    report_parser.add_argument("--top", type=int, default=10, help="Number of latest rankings to display")
    report_parser.add_argument(
        "--signal",
        choices=["STRONG", "WATCH", "NEUTRAL", "WEAK", "ERROR"],
        help="Filter latest rankings by signal",
    )

    serve_parser = subparsers.add_parser("serve", help="Serve the generated dashboard locally")
    serve_parser.add_argument(
        "--site-dir",
        default="site",
        help="Directory containing generated dashboard files",
    )
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    serve_parser.add_argument(
        "--log",
        default="logs/stock_analyzer.log",
        help="Path to log file",
    )

    rebalance_parser = subparsers.add_parser("rebalance", help="Build a monthly rebalance recommendation")
    rebalance_parser.add_argument(
        "--db",
        default="data/stock_analyzer.db",
        help="Path to SQLite database file",
    )
    rebalance_parser.add_argument(
        "--log",
        default="logs/stock_analyzer.log",
        help="Path to log file",
    )
    rebalance_parser.add_argument(
        "--holdings",
        help="Comma-separated current holdings, for example NVDA,AMZN,AMD",
    )
    rebalance_parser.add_argument(
        "--holdings-file",
        help="Path to a text file with one current holding ticker per line",
    )
    rebalance_parser.add_argument(
        "--top-n",
        type=int,
        help="Target number of stock positions; defaults to the current holdings count",
    )
    rebalance_parser.add_argument(
        "--buy-score",
        type=int,
        default=70,
        help="Minimum score required for a new buy",
    )
    rebalance_parser.add_argument(
        "--sell-score",
        type=int,
        default=55,
        help="Sell when a holding falls below this score",
    )
    rebalance_parser.add_argument(
        "--rotation-score-gap",
        type=int,
        default=10,
        help="Minimum score advantage a buy needs to replace an otherwise eligible holding",
    )

    prices_parser = subparsers.add_parser("prices", help="Show saved price history for one ticker")
    prices_parser.add_argument("ticker", help="Ticker symbol, for example NVDA")
    prices_parser.add_argument(
        "--db",
        default="data/stock_analyzer.db",
        help="Path to SQLite database file",
    )
    prices_parser.add_argument(
        "--log",
        default="logs/stock_analyzer.log",
        help="Path to log file",
    )
    prices_parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Maximum number of saved rows to display",
    )

    return parser.parse_args(argv)


def _build_failure_result(input_path: str, error: Exception) -> dict[str, object]:
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "strategy": "momentum",
        "benchmark": "QQQ",
        "run_status": "failed",
        "market_status": {},
        "rankings": [],
        "failure_error": f"{type(error).__name__}: {error}",
        "source_input": input_path,
    }


def main() -> int:
    args = parse_args()
    logger = configure_logging(Path(args.log))

    try:
        if args.command == "scan":
            logger.info(
                "Starting scan input=%s output=%s db=%s dashboard=%s email_report=%s",
                args.input,
                args.output,
                args.db,
                args.dashboard_output,
                args.email_report,
            )
            try:
                results = run_analysis(args.input)
                write_json(args.output, results)
                db_path = Path(args.db)
                initialize_database(db_path)
                run_id = save_analysis_result(db_path, results, source_input=args.input)
                dashboard_path = build_dashboard(db_path, args.dashboard_output)
                recent_runs = get_recent_full_runs(
                    db_path, limit=2, scoring_version=results.get("scoring_version")
                )
                latest_run = recent_runs[0] if recent_runs else None
                previous_run = recent_runs[1] if len(recent_runs) > 1 else None
                if args.email_report:
                    calendar_name = str((results.get("market_status") or {}).get("calendar") or "NYSE")
                    if monthly_rebalance_due(results.get("generated_at"), calendar_name):
                        send_scan_email_report(
                            results,
                            latest_run=latest_run,
                            previous_run=previous_run,
                            holdings_file=args.holdings_file,
                            monthly_action_required=True,
                        )
                        logger.info(
                            "Monthly action email sent to configured recipient holdings_file=%s",
                            args.holdings_file,
                        )
                    else:
                        logger.info("Successful scan email withheld until the monthly rebalance date")
            except Exception as exc:
                logger.exception("Scan failed")
                if args.email_report:
                    try:
                        send_scan_email_report(
                            _build_failure_result(args.input, exc),
                            holdings_file=args.holdings_file,
                        )
                        logger.info(
                            "Failure email report sent to configured recipient holdings_file=%s",
                            args.holdings_file,
                        )
                    except Exception:
                        logger.exception("Unable to send failure email report")
                return 1
            logger.info(
                "Completed scan run_id=%s run_status=%s rankings=%s generated_at=%s dashboard=%s",
                run_id,
                results.get("run_status"),
                len(results.get("rankings", [])),
                results.get("generated_at"),
                dashboard_path,
            )
            print(
                f"scan complete: run_id={run_id} "
                f"status={results.get('run_status')} "
                f"rankings={len(results.get('rankings', []))} "
                f"dashboard={dashboard_path}"
                + (" email=sent" if args.email_report else "")
            )
            return 0

        if args.command == "serve":
            logger.info("Starting local server site_dir=%s host=%s port=%s", args.site_dir, args.host, args.port)
            serve_site(args.site_dir, host=args.host, port=args.port)
            logger.info("Stopped local server")
            return 0

        if args.command == "rebalance":
            logger.info(
                "Building rebalance recommendation db=%s holdings=%s holdings_file=%s top_n=%s buy_score=%s sell_score=%s",
                args.db,
                args.holdings,
                args.holdings_file,
                args.top_n,
                args.buy_score,
                args.sell_score,
            )
            runs = get_recent_full_runs(
                Path(args.db), limit=2, scoring_version="monthly_momentum_v2"
            )
            if not runs:
                print(
                    "No monthly_momentum_v2 scans are available yet. "
                    "Run a new scan before requesting a rebalance recommendation."
                )
                return 0
            latest_run = runs[0] if runs else None
            previous_run = runs[1] if len(runs) > 1 else None
            holdings = load_holdings(args.holdings, args.holdings_file)
            report = build_rebalance_plan(
                latest_run,
                previous_run,
                holdings,
                top_n=args.top_n,
                buy_score=args.buy_score,
                sell_score=args.sell_score,
                rotation_score_gap=args.rotation_score_gap,
            )
            print(build_rebalance_report_text(report))
            logger.info(
                "Completed rebalance report latest_run_id=%s holdings=%s buy_count=%s sell_count=%s target_positions=%s",
                report.get("latest_run_id"),
                report.get("summary", {}).get("current_holdings_count"),
                report.get("summary", {}).get("buy_count"),
                report.get("summary", {}).get("sell_count"),
                report.get("summary", {}).get("target_positions_count"),
            )
            return 0

        if args.command == "prices":
            db_path = Path(args.db)
            normalized_ticker = args.ticker.strip().upper()
            logger.info(
                "Showing price history db=%s ticker=%s limit=%s",
                args.db,
                normalized_ticker,
                args.limit,
            )
            rows = get_price_history(db_path, normalized_ticker, limit=args.limit)
            print(build_price_history_text(normalized_ticker, rows))
            logger.info(
                "Completed price history ticker=%s rows=%s",
                normalized_ticker,
                len(rows),
            )
            return 0

        db_path = Path(args.db)
        logger.info(
            "Generating report db=%s runs=%s top=%s signal=%s",
            args.db,
            args.runs,
            args.top,
            args.signal,
        )
        recent_runs = get_recent_runs(db_path, limit=args.runs)
        latest_rankings = get_latest_rankings(db_path, top=args.top, signal=args.signal)
        print(build_report_text(recent_runs, latest_rankings))
        logger.info(
            "Completed report recent_runs=%s latest_rankings=%s",
            len(recent_runs),
            len(latest_rankings),
        )
        return 0
    except Exception:
        logger.exception("Unhandled failure in command=%s", args.command)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
