from __future__ import annotations

import pandas as pd
import yfinance as yf

from providers.base_provider import MarketDataProvider


class YFinanceProvider(MarketDataProvider):
    def get_history(self, ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        history = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
        if history.empty:
            raise ValueError(f"No price history returned for {ticker}")

        history = history.rename(columns=str.lower)
        required = {"open", "high", "low", "close", "volume"}
        missing = required.difference(history.columns)
        if missing:
            raise ValueError(f"Missing required columns for {ticker}: {sorted(missing)}")

        return history
