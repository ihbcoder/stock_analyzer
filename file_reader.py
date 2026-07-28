from __future__ import annotations

import json
from pathlib import Path

from models import AgentConfig, InputConfig, StockConfig


def load_input_config(path: str | Path) -> InputConfig:
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    agent_payload = payload.get("agent", {})
    stocks_payload = payload.get("stocks", [])

    agent = AgentConfig(
        strategy=agent_payload.get("strategy", "momentum"),
        benchmark=agent_payload.get("benchmark", "QQQ"),
        minimum_score=int(agent_payload.get("minimum_score", 70)),
        market_hours_only=bool(agent_payload.get("market_hours_only", False)),
    )

    stocks = [
        StockConfig(
            ticker=item["ticker"].upper(),
            name=item.get("name"),
            enabled=bool(item.get("enabled", True)),
        )
        for item in stocks_payload
    ]

    return InputConfig(agent=agent, stocks=stocks)
