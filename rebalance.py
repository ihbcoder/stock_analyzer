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
    rotation_score_gap: int = 10,
    minimum_average_dollar_volume: float | None = None,
) -> dict[str, Any]:
    latest_rankings = list((latest_run or {}).get("rankings", []) or [])
    previous_rankings = list((previous_run or {}).get("rankings", []) or [])

    latest_by_ticker = {str(row.get("ticker", "")).upper(): row for row in latest_rankings}
    previous_by_ticker = {str(row.get("ticker", "")).upper(): row for row in previous_rankings}
    policy = (latest_run or {}).get("portfolio_policy", {}) or {}
    minimum_average_dollar_volume = float(
        minimum_average_dollar_volume
        if minimum_average_dollar_volume is not None
        else policy.get("minimum_average_dollar_volume", 10_000_000)
    )
    market_regime = (latest_run or {}).get("market_regime", {}) or {}

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
                "momentum_change": _score_change(latest, previous),
            }
        )

    eligible_buys = [
        row
        for row in latest_rankings
        if str(row.get("ticker", "")).upper() not in current_holdings
        and int(row.get("score") or 0) >= buy_score
        and int(row.get("rank_position") or 999999) <= top_n
        and _has_positive_momentum(row)
        and _is_liquid(row, minimum_average_dollar_volume)
        and not market_regime.get("is_weak", False)
        and (_score_change(row, previous_by_ticker.get(str(row.get("ticker", "")).upper())) is None
             or _score_change(row, previous_by_ticker.get(str(row.get("ticker", "")).upper())) >= 0)
    ]
    _apply_rotation_gap(holding_rows, eligible_buys, rotation_score_gap)
    _limit_kept_holdings(holding_rows, top_n)
    kept_tickers = [row["ticker"] for row in holding_rows if row["action"] == "KEEP"]
    available_slots = max(0, top_n - len(kept_tickers))
    buy_rows = [
        {
            "ticker": row.get("ticker"),
            "name": row.get("name"),
            "action": "BUY",
            "reason": _buy_reason(row, previous_by_ticker.get(str(row.get("ticker", "")).upper()), top_n, buy_score),
            "rank_position": row.get("rank_position"),
            "previous_rank_position": previous_by_ticker.get(str(row.get('ticker', '')).upper(), {}).get("rank_position"),
            "score": row.get("score"),
            "signal": row.get("signal"),
            "price": row.get("price"),
            "momentum_change": _score_change(row, previous_by_ticker.get(str(row.get("ticker", "")).upper())),
        }
        for row in eligible_buys[:available_slots]
    ]

    target_tickers = kept_tickers + [str(row["ticker"]).upper() for row in buy_rows]
    target_allocations: list[dict[str, Any]] = []
    stock_weight = 100.0 / top_n if top_n else 0.0
    for ticker in target_tickers:
        latest = latest_by_ticker.get(ticker, {})
        source = "KEEP" if ticker in kept_tickers else "BUY"
        target_allocations.append(
            {
                "ticker": ticker,
                "name": latest.get("name"),
                "source": source,
                "target_weight_pct": stock_weight,
                "rank_position": latest.get("rank_position"),
                "score": latest.get("score"),
                "signal": latest.get("signal"),
                "price": latest.get("price"),
                "momentum_change": _score_change(latest, previous_by_ticker.get(ticker)),
            }
        )

    fallback_weight = max(0.0, 100.0 - stock_weight * len(target_tickers))
    if fallback_weight:
        for ticker in ("QQQ", "SPY"):
            target_allocations.append(
                {
                    "ticker": ticker,
                    "name": "In-market fallback allocation",
                    "source": "FALLBACK",
                    "target_weight_pct": fallback_weight / 2,
                    "rank_position": None,
                    "score": None,
                    "signal": market_regime.get("label", "FALLBACK"),
                    "price": None,
                    "momentum_change": None,
                }
            )

    fallback_destination = "50% QQQ / 50% SPY" if fallback_weight else "qualified stock replacements"
    for row in holding_rows:
        if row["action"] == "SELL":
            row["destination"] = fallback_destination
        else:
            row["destination"] = "CURRENT HOLDING"

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
        "rotation_score_gap": rotation_score_gap,
        "minimum_average_dollar_volume": minimum_average_dollar_volume,
        "market_regime": market_regime,
        "fallback_allocation_pct": fallback_weight,
        "market_status": (latest_run or {}).get("market_status", {}),
        "current_holdings": holding_rows,
        "buy_candidates": buy_rows,
        "target_allocations": target_allocations,
        "summary": {
            "current_holdings_count": len(current_holdings),
            "keep_count": sum(1 for row in holding_rows if row["action"] == "KEEP"),
            "sell_count": sum(1 for row in holding_rows if row["action"] == "SELL"),
            "buy_count": len(buy_rows),
            "fallback_allocation_pct": fallback_weight,
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


def _score_change(latest: dict[str, Any] | None, previous: dict[str, Any] | None) -> int | None:
    if latest is None or previous is None:
        return None
    try:
        return int(latest.get("score")) - int(previous.get("score"))
    except (TypeError, ValueError):
        return None


def _has_positive_momentum(row: dict[str, Any]) -> bool:
    metrics = row.get("metrics", {}) or {}
    try:
        return (
            float(metrics.get("return_21d")) > 0
            and float(metrics.get("return_63d")) > 0
            and float(metrics.get("relative_return_21d")) > 0
            and float(metrics.get("relative_return_63d")) > 0
        )
    except (TypeError, ValueError):
        return False


def _is_liquid(row: dict[str, Any], minimum_average_dollar_volume: float) -> bool:
    try:
        return float((row.get("metrics", {}) or {}).get("average_dollar_volume_20")) >= minimum_average_dollar_volume
    except (TypeError, ValueError):
        return False


def _limit_kept_holdings(holding_rows: list[dict[str, Any]], top_n: int) -> None:
    kept_rows = [row for row in holding_rows if row["action"] == "KEEP"]
    kept_rows.sort(
        key=lambda row: (
            -(int(row.get("score") or 0)),
            int(row.get("rank_position") or 999999),
            str(row.get("ticker") or ""),
        )
    )
    for row in kept_rows[top_n:]:
        row["action"] = "SELL"
        row["reason"] = f"outside the target portfolio size of {top_n}"


def _buy_reason(row: dict[str, Any], previous: dict[str, Any] | None, top_n: int, buy_score: int) -> str:
    change = _score_change(row, previous)
    acceleration = "score change unavailable (first v2 scan)" if change is None else f"score change {change:+d}"
    return f"rank <= {top_n}, score >= {buy_score}, positive 1m/3m returns, {acceleration}"


def _apply_rotation_gap(
    holding_rows: list[dict[str, Any]], eligible_buys: list[dict[str, Any]], rotation_score_gap: int,
) -> None:
    """Avoid replacing a non-qualifying holding for a nearly tied candidate."""
    if not eligible_buys:
        return
    best_buy_score = max(int(row.get("score") or 0) for row in eligible_buys)
    for row in holding_rows:
        if row["action"] != "SELL" or not str(row.get("reason", "")).startswith("outside top"):
            continue
        holding_score = int(row.get("score") or 0)
        if best_buy_score < holding_score + rotation_score_gap:
            row["action"] = "KEEP"
            row["reason"] = (
                f"outside top group, but no buy candidate exceeds score {holding_score} "
                f"by the {rotation_score_gap}-point rotation gap"
            )
