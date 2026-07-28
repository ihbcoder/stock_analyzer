from __future__ import annotations

import argparse
import sys
from pathlib import Path

from analyzer import run_analysis
from app_logging import configure_logging
from dashboard import build_dashboard
from db import get_latest_rankings, get_recent_runs, initialize_database, save_analysis_result
from file_writer import write_json
from reporting import build_report_text
from site_server import serve_site


def parse_args() -> argparse.Namespace:
    argv = sys.argv[1:]
    if argv and argv[0] not in {"scan", "report", "serve", "-h", "--help"}:
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

    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    logger = configure_logging(Path(args.log))

    try:
        if args.command == "scan":
            logger.info(
                "Starting scan input=%s output=%s db=%s dashboard=%s",
                args.input,
                args.output,
                args.db,
                args.dashboard_output,
            )
            results = run_analysis(args.input)
            write_json(args.output, results)
            db_path = Path(args.db)
            initialize_database(db_path)
            run_id = save_analysis_result(db_path, results, source_input=args.input)
            dashboard_path = build_dashboard(db_path, args.dashboard_output)
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
            )
            return 0

        if args.command == "serve":
            logger.info("Starting local server site_dir=%s host=%s port=%s", args.site_dir, args.host, args.port)
            serve_site(args.site_dir, host=args.host, port=args.port)
            logger.info("Stopped local server")
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
