from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentConfig:
    strategy: str = "momentum"
    benchmark: str = "QQQ"
    minimum_score: int = 70
    market_hours_only: bool = False


@dataclass(slots=True)
class StockConfig:
    ticker: str
    name: str | None = None
    enabled: bool = True


@dataclass(slots=True)
class InputConfig:
    agent: AgentConfig
    stocks: list[StockConfig]


@dataclass(slots=True)
class StockAnalysis:
    ticker: str
    name: str | None
    price: float | None
    score: int
    signal: str
    metrics: dict[str, float | None] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    status: str = "success"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
