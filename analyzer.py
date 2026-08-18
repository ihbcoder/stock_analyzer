from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from file_reader import load_input_config
from market_hours import get_market_status
from metrics import build_metrics
from models import StockAnalysis
from providers import MarketDataProvider, YFinanceProvider
from scoring import score_stock


def run_analysis(input_path: str, provider: MarketDataProvider | None = None) -> dict:
    config = load_input_config(input_path)
    market_data = provider or YFinanceProvider()
    generated_at = datetime.now(ZoneInfo("America/New_York")).isoformat()
    market_status = get_market_status()

    if config.agent.market_hours_only and not market_status["is_open"]:
        return {
            "generated_at": generated_at,
            "strategy": config.agent.strategy,
            "benchmark": config.agent.benchmark,
            "minimum_score": config.agent.minimum_score,
            "scoring_version": config.agent.scoring_version,
            "market_hours_only": config.agent.market_hours_only,
            "run_status": "skipped_market_closed",
            "market_status": market_status,
            "rankings": [],
        }

    benchmark_history = market_data.get_history(config.agent.benchmark)
    benchmark_metrics = build_metrics(benchmark_history)
    benchmark_row = benchmark_metrics.iloc[-1].to_dict()
    benchmark_summary = _benchmark_summary(benchmark_row)
    market_regime = _market_regime(benchmark_summary, config.agent.market_volatility_limit)

    candidates: list[tuple[str, str | None, dict]] = []
    analyses: list[StockAnalysis] = []

    for stock in config.stocks:
        if not stock.enabled:
            continue

        try:
            history = market_data.get_history(stock.ticker)
            metric_frame = build_metrics(history)
            latest = metric_frame.iloc[-1].to_dict()
            candidates.append((stock.ticker, stock.name, latest))
        except Exception as exc:
            analysis = StockAnalysis(
                ticker=stock.ticker,
                name=stock.name,
                price=None,
                score=0,
                signal="ERROR",
                status="error",
                error=str(exc),
            )
            analyses.append(analysis)

    relative_strength = _relative_strength_percentiles(candidates, benchmark_row)
    one_month_relative_strength = _one_month_relative_strength_percentiles(candidates, benchmark_row)
    for ticker, name, latest in candidates:
        analyses.append(
            score_stock(
                ticker=ticker,
                name=name,
                stock_row=latest,
                benchmark_row=benchmark_row,
                minimum_score=config.agent.minimum_score,
                relative_strength_percentile=relative_strength.get(ticker),
                one_month_relative_strength_percentile=one_month_relative_strength.get(ticker),
            )
        )

    analyses.sort(key=lambda item: item.score, reverse=True)

    return {
        "generated_at": generated_at,
        "strategy": config.agent.strategy,
        "benchmark": config.agent.benchmark,
        "minimum_score": config.agent.minimum_score,
        "scoring_version": config.agent.scoring_version,
        "benchmark_metrics": benchmark_summary,
        "market_regime": market_regime,
        "portfolio_policy": _portfolio_policy(config),
        "market_hours_only": config.agent.market_hours_only,
        "run_status": "success",
        "market_status": market_status,
        "rankings": [item.to_dict() for item in analyses],
    }


def _relative_strength_percentiles(
    candidates: list[tuple[str, str | None, dict]], benchmark_row: dict,
) -> dict[str, float | None]:
    """Rank each stock's average 3-, 6-, and 12-month excess return in the watchlist."""
    horizons = (63, 126, 252)
    values: dict[str, float] = {}
    for ticker, _, row in candidates:
        excess_returns = []
        for horizon in horizons:
            stock_return = _as_float(row.get(f"return_{horizon}d"))
            benchmark_return = _as_float(benchmark_row.get(f"return_{horizon}d"))
            if stock_return is not None and benchmark_return is not None:
                excess_returns.append(stock_return - benchmark_return)
        if excess_returns:
            values[ticker] = sum(excess_returns) / len(excess_returns)
    return _percentile_ranks(values)


def _one_month_relative_strength_percentiles(
    candidates: list[tuple[str, str | None, dict]], benchmark_row: dict,
) -> dict[str, float | None]:
    benchmark_return = _as_float(benchmark_row.get("return_21d"))
    values = {
        ticker: stock_return - benchmark_return
        for ticker, _, row in candidates
        if (stock_return := _as_float(row.get("return_21d"))) is not None and benchmark_return is not None
    }
    return _percentile_ranks(values)


def _percentile_ranks(values: dict[str, float]) -> dict[str, float | None]:
    if not values:
        return {}
    series = pd.Series(values, dtype="float64")
    return {ticker: float(percentile) for ticker, percentile in series.rank(pct=True).items()}


def _as_float(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if pd.notna(numeric) else None


def _benchmark_summary(row: dict) -> dict[str, float | None]:
    return {
        "price": _as_float(row.get("close")),
        "sma_200": _as_float(row.get("sma_200")),
        "annualized_volatility_20": _as_float(row.get("annualized_volatility_20")),
    }


def _market_regime(benchmark: dict[str, float | None], volatility_limit: float) -> dict[str, object]:
    price = benchmark.get("price")
    sma_200 = benchmark.get("sma_200")
    volatility = benchmark.get("annualized_volatility_20")
    reasons: list[str] = []
    if price is None or sma_200 is None:
        reasons.append("QQQ 200-day trend is unavailable")
    elif price <= sma_200:
        reasons.append("QQQ is at or below its 200-day average")
    if volatility is not None and volatility > volatility_limit:
        reasons.append(f"QQQ 20-day annualized volatility is above {volatility_limit:.0%}")
    return {
        "is_weak": bool(reasons),
        "label": "WEAK" if reasons else "HEALTHY",
        "reason": "; ".join(reasons) if reasons else "QQQ trend and volatility are within policy limits",
    }


def _portfolio_policy(config) -> dict[str, object]:
    return {
        "fallback_allocations": {"QQQ": 0.5, "SPY": 0.5},
        "minimum_average_dollar_volume": config.agent.minimum_average_dollar_volume,
        "market_volatility_limit": config.agent.market_volatility_limit,
    }
