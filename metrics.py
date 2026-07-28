from __future__ import annotations

import pandas as pd

from indicators import distance_from_high, ema, macd, percent_return, relative_volume, rsi, sma


def build_metrics(history: pd.DataFrame) -> pd.DataFrame:
    frame = history.copy()
    close = frame["close"]
    volume = frame["volume"]

    frame["ema_20"] = ema(close, 20)
    frame["sma_50"] = sma(close, 50)
    frame["sma_200"] = sma(close, 200)
    frame["return_5d"] = percent_return(close, 5)
    frame["return_20d"] = percent_return(close, 20)
    frame["return_60d"] = percent_return(close, 60)
    frame["rsi_14"] = rsi(close, 14)
    frame["relative_volume_20"] = relative_volume(volume, 20)
    frame["distance_from_52_week_high"] = distance_from_high(close, 252)

    macd_line, macd_signal, macd_histogram = macd(close)
    frame["macd"] = macd_line
    frame["macd_signal"] = macd_signal
    frame["macd_histogram"] = macd_histogram

    return frame
