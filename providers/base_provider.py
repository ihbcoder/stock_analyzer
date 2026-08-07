from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class MarketDataProvider(ABC):
    @abstractmethod
    def get_history(self, ticker: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        raise NotImplementedError
