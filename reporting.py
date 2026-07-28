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
