from __future__ import annotations

from models import StockAnalysis


def score_stock(
    ticker: str,
    name: str | None,
    stock_row: dict[str, float | None],
    benchmark_row: dict[str, float | None],
    minimum_score: int,
    relative_strength_percentile: float | None = None,
    one_month_relative_strength_percentile: float | None = None,
) -> StockAnalysis:
    score = 0
    reasons: list[str] = []
    risk_flags: list[str] = []

    price = _as_float(stock_row.get("close"))
    sma_50 = _as_float(stock_row.get("sma_50"))
    sma_200 = _as_float(stock_row.get("sma_200"))
    return_21d = _as_float(stock_row.get("return_21d"))
    return_63d = _as_float(stock_row.get("return_63d"))
    return_126d = _as_float(stock_row.get("return_126d"))
    return_252d = _as_float(stock_row.get("return_252d"))
    rsi_14 = _as_float(stock_row.get("rsi_14"))
    rel_vol = _as_float(stock_row.get("relative_volume_20"))
    dist_high = _as_float(stock_row.get("distance_from_52_week_high"))
    benchmark_21d = _as_float(benchmark_row.get("return_21d"))
    benchmark_63d = _as_float(benchmark_row.get("return_63d"))
    benchmark_126d = _as_float(benchmark_row.get("return_126d"))
    benchmark_252d = _as_float(benchmark_row.get("return_252d"))

    if relative_strength_percentile is not None:
        relative_strength_points = round(50 * relative_strength_percentile)
        score += relative_strength_points
        reasons.append(f"Multi-horizon relative strength is in the {relative_strength_percentile * 100:.0f}th percentile")
    if one_month_relative_strength_percentile is not None:
        one_month_points = round(15 * one_month_relative_strength_percentile)
        score += one_month_points
        reasons.append(f"One-month relative strength is in the {one_month_relative_strength_percentile * 100:.0f}th percentile")

    if _gt(price, sma_50):
        score += 10
        reasons.append("Price is above the 50-day SMA")
    if _gt(price, sma_200):
        score += 10
        reasons.append("Price is above the 200-day SMA")
    if rsi_14 is not None and rsi_14 > 80:
        risk_flags.append("RSI is very extended")

    if dist_high is not None and dist_high >= -0.10:
        score += 15
        reasons.append("Trading within 10% of the 52-week high")
    elif dist_high is not None and dist_high < -0.25:
        risk_flags.append("Far below the 52-week high")

    signal = classify_score(score, minimum_score)
    metrics = {
        "price": price,
        "return_5d": _as_float(stock_row.get("return_5d")),
        "return_20d": _as_float(stock_row.get("return_20d")),
        "return_60d": _as_float(stock_row.get("return_60d")),
        "return_21d": return_21d,
        "return_63d": return_63d,
        "return_126d": return_126d,
        "return_252d": return_252d,
        "rsi_14": rsi_14,
        "relative_volume_20": rel_vol,
        "distance_from_52_week_high": dist_high,
        "benchmark_return_21d": benchmark_21d,
        "benchmark_return_63d": benchmark_63d,
        "benchmark_return_126d": benchmark_126d,
        "benchmark_return_252d": benchmark_252d,
        "relative_return_21d": _difference(return_21d, benchmark_21d),
        "relative_return_63d": _difference(return_63d, benchmark_63d),
        "relative_return_126d": _difference(return_126d, benchmark_126d),
        "relative_return_252d": _difference(return_252d, benchmark_252d),
        "relative_strength_percentile": relative_strength_percentile,
        "one_month_relative_strength_percentile": one_month_relative_strength_percentile,
    }

    return StockAnalysis(
        ticker=ticker,
        name=name,
        price=price,
        score=score,
        signal=signal,
        metrics=metrics,
        reasons=reasons,
        risk_flags=risk_flags,
    )


def classify_score(score: int, minimum_score: int) -> str:
    strong_threshold = max(minimum_score + 10, 80)
    if score >= strong_threshold:
        return "STRONG"
    if score >= minimum_score:
        return "WATCH"
    if score >= 55:
        return "NEUTRAL"
    return "WEAK"


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric:
        return None
    return numeric


def _gt(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and left > right


def _difference(left: float | None, right: float | None) -> float | None:
    return left - right if left is not None and right is not None else None
