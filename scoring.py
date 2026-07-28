from __future__ import annotations

from models import StockAnalysis


def score_stock(
    ticker: str,
    name: str | None,
    stock_row: dict[str, float | None],
    benchmark_row: dict[str, float | None],
    minimum_score: int,
) -> StockAnalysis:
    score = 0
    reasons: list[str] = []
    risk_flags: list[str] = []

    price = _as_float(stock_row.get("close"))
    ema_20 = _as_float(stock_row.get("ema_20"))
    sma_50 = _as_float(stock_row.get("sma_50"))
    sma_200 = _as_float(stock_row.get("sma_200"))
    return_5d = _as_float(stock_row.get("return_5d"))
    return_20d = _as_float(stock_row.get("return_20d"))
    return_60d = _as_float(stock_row.get("return_60d"))
    rsi_14 = _as_float(stock_row.get("rsi_14"))
    rel_vol = _as_float(stock_row.get("relative_volume_20"))
    dist_high = _as_float(stock_row.get("distance_from_52_week_high"))
    macd_value = _as_float(stock_row.get("macd"))
    macd_signal = _as_float(stock_row.get("macd_signal"))
    benchmark_20d = _as_float(benchmark_row.get("return_20d"))
    benchmark_60d = _as_float(benchmark_row.get("return_60d"))

    if _gt(price, ema_20):
        score += 8
        reasons.append("Price is above the 20-day EMA")
    if _gt(price, sma_50):
        score += 8
        reasons.append("Price is above the 50-day SMA")
    if _gt(price, sma_200):
        score += 9
        reasons.append("Price is above the 200-day SMA")

    if _gt(return_20d, benchmark_20d):
        score += 10
        reasons.append("Outperformed the benchmark over 20 days")
    if _gt(return_60d, benchmark_60d):
        score += 10
        reasons.append("Outperformed the benchmark over 60 days")

    if _gt(return_5d, 0):
        score += 5
        reasons.append("Positive 5-day return")
    if _gt(return_20d, 0):
        score += 7
        reasons.append("Positive 20-day return")
    if _gt(return_60d, 0):
        score += 8
        reasons.append("Positive 60-day return")

    if rsi_14 is not None and 55 <= rsi_14 <= 72:
        score += 6
        reasons.append("RSI is in a healthy momentum range")
    elif rsi_14 is not None and rsi_14 > 80:
        risk_flags.append("RSI is very extended")

    if _gt(macd_value, macd_signal):
        score += 4
        reasons.append("MACD is above its signal line")

    if _gt(rel_vol, 1.25):
        score += 10
        reasons.append("Volume is above the 20-day average")

    if dist_high is not None and dist_high >= -0.10:
        score += 10
        reasons.append("Trading within 10% of the 52-week high")
    elif dist_high is not None and dist_high < -0.25:
        risk_flags.append("Far below the 52-week high")

    if price is not None and ema_20 is not None and price > ema_20 * 1.15:
        risk_flags.append("Price is more than 15% above the 20-day EMA")

    signal = classify_score(score, minimum_score)
    metrics = {
        "price": price,
        "return_5d": return_5d,
        "return_20d": return_20d,
        "return_60d": return_60d,
        "rsi_14": rsi_14,
        "relative_volume_20": rel_vol,
        "distance_from_52_week_high": dist_high,
        "macd": macd_value,
        "macd_signal": macd_signal,
        "benchmark_return_20d": benchmark_20d,
        "benchmark_return_60d": benchmark_60d,
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
