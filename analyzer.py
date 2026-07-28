from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

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
            "market_hours_only": config.agent.market_hours_only,
            "run_status": "skipped_market_closed",
            "market_status": market_status,
            "rankings": [],
        }

    benchmark_history = market_data.get_history(config.agent.benchmark)
    benchmark_metrics = build_metrics(benchmark_history)
    benchmark_row = benchmark_metrics.iloc[-1].to_dict()

    analyses: list[StockAnalysis] = []

    for stock in config.stocks:
        if not stock.enabled:
            continue

        try:
            history = market_data.get_history(stock.ticker)
            metric_frame = build_metrics(history)
            latest = metric_frame.iloc[-1].to_dict()
            analysis = score_stock(
                ticker=stock.ticker,
                name=stock.name,
                stock_row=latest,
                benchmark_row=benchmark_row,
                minimum_score=config.agent.minimum_score,
            )
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

    analyses.sort(key=lambda item: item.score, reverse=True)

    return {
        "generated_at": generated_at,
        "strategy": config.agent.strategy,
        "benchmark": config.agent.benchmark,
        "minimum_score": config.agent.minimum_score,
        "market_hours_only": config.agent.market_hours_only,
        "run_status": "success",
        "market_status": market_status,
        "rankings": [item.to_dict() for item in analyses],
    }
