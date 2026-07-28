from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import pandas_market_calendars as mcal

EASTERN_TZ = ZoneInfo("America/New_York")


def get_market_status(
    calendar_name: str = "NYSE",
    now: datetime | None = None,
) -> dict[str, Any]:
    current_time = (now or datetime.now(EASTERN_TZ)).astimezone(EASTERN_TZ)
    calendar = mcal.get_calendar(calendar_name)

    start_date = current_time.date() - timedelta(days=7)
    end_date = current_time.date() + timedelta(days=14)
    schedule = calendar.schedule(start_date=start_date, end_date=end_date)

    if schedule.empty:
        return {
            "calendar": calendar_name,
            "checked_at": current_time.isoformat(),
            "is_open": False,
            "reason": "No trading sessions found in schedule window",
            "opens_at": None,
            "closes_at": None,
            "session_date": None,
            "next_open_at": None,
        }

    schedule = schedule.copy()
    schedule["market_open"] = pd.to_datetime(schedule["market_open"]).dt.tz_convert(EASTERN_TZ)
    schedule["market_close"] = pd.to_datetime(schedule["market_close"]).dt.tz_convert(EASTERN_TZ)

    for session_date, row in schedule.iterrows():
        market_open = row["market_open"]
        market_close = row["market_close"]
        if market_open <= current_time <= market_close:
            return {
                "calendar": calendar_name,
                "checked_at": current_time.isoformat(),
                "is_open": True,
                "reason": "Market is open",
                "opens_at": market_open.isoformat(),
                "closes_at": market_close.isoformat(),
                "session_date": str(session_date.date()),
                "next_open_at": None,
            }

    future_sessions = schedule[schedule["market_open"] > current_time]
    next_open_at = None
    reason = "Market is closed"
    opens_at = None
    closes_at = None
    session_date = None

    if not future_sessions.empty:
        next_session_date = future_sessions.index[0]
        next_row = future_sessions.iloc[0]
        next_open_at = next_row["market_open"].isoformat()

    same_day_sessions = schedule[schedule.index.date == current_time.date()]
    if not same_day_sessions.empty:
        row = same_day_sessions.iloc[0]
        opens_at = row["market_open"].isoformat()
        closes_at = row["market_close"].isoformat()
        session_date = str(same_day_sessions.index[0].date())
        if current_time < row["market_open"]:
            reason = "Market has not opened yet"
        elif current_time > row["market_close"]:
            reason = "Market is closed for the day"
    else:
        reason = "Market is closed today"

    return {
        "calendar": calendar_name,
        "checked_at": current_time.isoformat(),
        "is_open": False,
        "reason": reason,
        "opens_at": opens_at,
        "closes_at": closes_at,
        "session_date": session_date,
        "next_open_at": next_open_at,
    }
