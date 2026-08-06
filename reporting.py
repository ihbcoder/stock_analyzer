from __future__ import annotations

from typing import Any


def build_report_text(recent_runs: list[dict[str, Any]], latest_rankings: list[dict[str, Any]]) -> str:
    sections: list[str] = []

    if recent_runs:
        run_rows = [
            [
                str(row["id"]),
                row["generated_at"],
                row["benchmark"],
                str(row["minimum_score"]),
                str(row["stock_count"]),
                row.get("run_status") or "",
                row["source_input"],
            ]
            for row in recent_runs
        ]
        sections.append(
            "Recent runs\n"
            + _format_table(
                ["run_id", "generated_at", "benchmark", "min_score", "stocks", "status", "source_input"],
                run_rows,
            )
        )
    else:
        sections.append("Recent runs\n(no saved runs found)")

    if latest_rankings:
        ranking_rows = [
            [
                str(row["rank_position"]),
                row["ticker"],
                row.get("signal") or "",
                str(row.get("score") or ""),
                _format_price(row.get("price")),
                row.get("status") or "",
            ]
            for row in latest_rankings
        ]
        sections.append(
            "Latest rankings\n"
            + _format_table(
                ["rank", "ticker", "signal", "score", "price", "status"],
                ranking_rows,
            )
        )
    else:
        sections.append("Latest rankings\n(no rankings found)")

    return "\n\n".join(sections)


def build_rebalance_report_text(report: dict[str, Any]) -> str:
    sections: list[str] = []
    summary = report.get("summary", {})
    market_status = report.get("market_status", {})

    summary_rows = [
        ["latest_run_id", str(report.get("latest_run_id") or "")],
        ["generated_at", str(report.get("generated_at") or "")],
        ["top_n", str(report.get("top_n") or "")],
        ["buy_score", str(report.get("buy_score") or "")],
        ["sell_score", str(report.get("sell_score") or "")],
        ["market_state", "OPEN" if market_status.get("is_open") else "CLOSED"],
        ["market_reason", str(market_status.get("reason") or "")],
        ["current_holdings", str(summary.get("current_holdings_count") or 0)],
        ["keep_count", str(summary.get("keep_count") or 0)],
        ["sell_count", str(summary.get("sell_count") or 0)],
        ["buy_count", str(summary.get("buy_count") or 0)],
        ["target_positions", str(summary.get("target_positions_count") or 0)],
    ]
    sections.append("Monthly rebalance summary\n" + _format_table(["field", "value"], summary_rows))

    current_holdings = report.get("current_holdings", [])
    if current_holdings:
        holding_rows = [
            [
                row["ticker"],
                row.get("action") or "",
                str(row.get("rank_position") or ""),
                str(row.get("previous_rank_position") or ""),
                str(row.get("score") or ""),
                row.get("signal") or "",
                _format_price(row.get("price")),
                row.get("reason") or "",
            ]
            for row in current_holdings
        ]
        sections.append(
            "Current holdings actions\n"
            + _format_table(
                ["ticker", "action", "rank", "prev_rank", "score", "signal", "price", "reason"],
                holding_rows,
            )
        )
    else:
        sections.append("Current holdings actions\n(no current holdings supplied)")

    buy_candidates = report.get("buy_candidates", [])
    if buy_candidates:
        buy_rows = [
            [
                row["ticker"],
                str(row.get("rank_position") or ""),
                str(row.get("score") or ""),
                row.get("signal") or "",
                _format_price(row.get("price")),
                row.get("reason") or "",
            ]
            for row in buy_candidates
        ]
        sections.append(
            "Buy candidates\n"
            + _format_table(
                ["ticker", "rank", "score", "signal", "price", "reason"],
                buy_rows,
            )
        )
    else:
        sections.append("Buy candidates\n(no buy candidates under current rules)")

    target_allocations = report.get("target_allocations", [])
    if target_allocations:
        target_rows = [
            [
                row["ticker"],
                row.get("source") or "",
                str(row.get("rank_position") or ""),
                str(row.get("score") or ""),
                row.get("signal") or "",
                _format_price(row.get("price")),
                f"{float(row.get('target_weight_pct') or 0):.1f}%",
            ]
            for row in target_allocations
        ]
        sections.append(
            "Suggested target allocation\n"
            + _format_table(
                ["ticker", "source", "rank", "score", "signal", "price", "target_weight"],
                target_rows,
            )
        )
    else:
        sections.append("Suggested target allocation\n(no target positions)")

    return "\n\n".join(sections)


def _format_price(value: Any) -> str:
    if value is None:
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return ""
    return f"{numeric:.2f}"


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def render_row(row: list[str]) -> str:
        return " | ".join(cell.ljust(widths[index]) for index, cell in enumerate(row))

    separator = "-+-".join("-" * width for width in widths)
    return "\n".join(
        [
            render_row(headers),
            separator,
            *[render_row(row) for row in rows],
        ]
    )
