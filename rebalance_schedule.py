from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import pandas_market_calendars as mcal


EASTERN_TZ = ZoneInfo("America/New_York")


def monthly_rebalance_due(generated_at: Any, calendar_name: str = "NYSE") -> bool:
    """Return true after the close on the first trading day of a month."""
    current_time = _parse_eastern_datetime(generated_at)
    month_start = current_time.date().replace(day=1)
    month_end = month_start.replace(day=28)
    calendar = mcal.get_calendar(calendar_name)
    schedule = calendar.schedule(start_date=month_start, end_date=month_end)
    if schedule.empty:
        return False

    first_session = schedule.iloc[0]
    first_session_date = schedule.index[0].date()
    close = pd.Timestamp(first_session["market_close"]).tz_convert(EASTERN_TZ)
    return current_time.date() == first_session_date and current_time >= close


def _parse_eastern_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value:
        parsed = datetime.fromisoformat(value)
    else:
        parsed = datetime.now(EASTERN_TZ)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=EASTERN_TZ)
    return parsed.astimezone(EASTERN_TZ)
