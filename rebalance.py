from __future__ import annotations

from pathlib import Path
from typing import Any


def load_holdings(holdings: str | None = None, holdings_file: str | Path | None = None) -> list[str]:
    tickers: list[str] = []

    if holdings:
        tickers.extend(_normalize_tickers(holdings.split(",")))

    if holdings_file:
        source = Path(holdings_file)
        if source.exists():
            tickers.extend(_normalize_tickers(source.read_text(encoding="utf-8").splitlines()))

    deduped: list[str] = []
    seen: set[str] = set()
    for ticker in tickers:
        if ticker not in seen:
            seen.add(ticker)
            deduped.append(ticker)
    return deduped


def build_rebalance_plan(
    latest_run: dict[str, Any] | None,
    previous_run: dict[str, Any] | None,
    current_holdings: list[str],
    *,
    top_n: int = 8,
    buy_score: int = 70,
    sell_score: int = 55,
) -> dict[str, Any]:
    latest_rankings = list((latest_run or {}).get("rankings", []) or [])
    previous_rankings = list((previous_run or {}).get("rankings", []) or [])

    latest_by_ticker = {str(row.get("ticker", "")).upper(): row for row in latest_rankings}
    previous_by_ticker = {str(row.get("ticker", "")).upper(): row for row in previous_rankings}

    current_holdings = [ticker.upper() for ticker in current_holdings]
    holding_rows: list[dict[str, Any]] = []
    kept_tickers: list[str] = []

    for ticker in current_holdings:
        latest = latest_by_ticker.get(ticker)
        previous = previous_by_ticker.get(ticker)
        action, reason = _decide_holding_action(
            ticker=ticker,
            latest=latest,
            previous=previous,
            top_n=top_n,
            sell_score=sell_score,
        )
        if action == "KEEP":
            kept_tickers.append(ticker)

        holding_rows.append(
            {
                "ticker": ticker,
                "name": (latest or previous or {}).get("name"),
                "action": action,
                "reason": reason,
                "rank_position": (latest or {}).get("rank_position"),
                "previous_rank_position": (previous or {}).get("rank_position"),
                "score": (latest or {}).get("score"),
                "signal": (latest or {}).get("signal"),
                "price": (latest or {}).get("price"),
            }
        )

    eligible_buys = [
        row
        for row in latest_rankings
        if str(row.get("ticker", "")).upper() not in current_holdings
        and int(row.get("score") or 0) >= buy_score
        and int(row.get("rank_position") or 999999) <= top_n
    ]
    available_slots = max(0, top_n - len(kept_tickers))
    buy_rows = [
        {
            "ticker": row.get("ticker"),
            "name": row.get("name"),
            "action": "BUY",
            "reason": f"rank <= {top_n} and score >= {buy_score}",
            "rank_position": row.get("rank_position"),
            "previous_rank_position": previous_by_ticker.get(str(row.get('ticker', '')).upper(), {}).get("rank_position"),
            "score": row.get("score"),
            "signal": row.get("signal"),
            "price": row.get("price"),
        }
        for row in eligible_buys[:available_slots]
    ]

    target_tickers = kept_tickers + [str(row["ticker"]).upper() for row in buy_rows]
    target_allocations: list[dict[str, Any]] = []
    weight = (100.0 / len(target_tickers)) if target_tickers else 0.0
    for ticker in target_tickers:
        latest = latest_by_ticker.get(ticker, {})
        source = "KEEP" if ticker in kept_tickers else "BUY"
        target_allocations.append(
            {
                "ticker": ticker,
                "name": latest.get("name"),
                "source": source,
                "target_weight_pct": weight,
                "rank_position": latest.get("rank_position"),
                "score": latest.get("score"),
                "signal": latest.get("signal"),
                "price": latest.get("price"),
            }
        )

    target_allocations.sort(
        key=lambda row: (
            999999 if row.get("rank_position") is None else int(row["rank_position"]),
            str(row.get("ticker") or ""),
        )
    )
    holding_rows.sort(key=lambda row: ({"SELL": 0, "KEEP": 1}.get(str(row.get("action")), 9), str(row.get("ticker") or "")))

    return {
        "generated_at": (latest_run or {}).get("generated_at"),
        "latest_run_id": (latest_run or {}).get("id"),
        "previous_run_id": (previous_run or {}).get("id"),
        "top_n": top_n,
        "buy_score": buy_score,
        "sell_score": sell_score,
        "market_status": (latest_run or {}).get("market_status", {}),
        "current_holdings": holding_rows,
        "buy_candidates": buy_rows,
        "target_allocations": target_allocations,
        "summary": {
            "current_holdings_count": len(current_holdings),
            "keep_count": sum(1 for row in holding_rows if row["action"] == "KEEP"),
            "sell_count": sum(1 for row in holding_rows if row["action"] == "SELL"),
            "buy_count": len(buy_rows),
            "target_positions_count": len(target_allocations),
        },
    }


def _normalize_tickers(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw_value in values:
        ticker = raw_value.strip().upper()
        if ticker:
            normalized.append(ticker)
    return normalized


def _decide_holding_action(
    *,
    ticker: str,
    latest: dict[str, Any] | None,
    previous: dict[str, Any] | None,
    top_n: int,
    sell_score: int,
) -> tuple[str, str]:
    if latest is None:
        return "SELL", "not ranked in latest run"

    latest_score = int(latest.get("score") or 0)
    latest_rank = latest.get("rank_position")
    previous_rank = (previous or {}).get("rank_position")

    if latest_score < sell_score:
        return "SELL", f"score {latest_score} is below sell threshold {sell_score}"

    if latest_rank is not None and int(latest_rank) <= top_n:
        return "KEEP", f"still inside top {top_n}"

    if previous_rank is not None and int(previous_rank) <= top_n:
        return "KEEP", f"outside top {top_n} this month, but was inside top {top_n} last run"

    return "SELL", f"outside top {top_n} for two runs"
