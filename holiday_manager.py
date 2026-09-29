"""
AGY QUANT PLATFORM: NSE HOLIDAY & TRADING SESSION MANAGER
Manages official NSE trading holidays and business day calculations.
Used to strictly exclude weekends and market holidays from:
- Hold Duration (Hold_Duration_Days counts actual trading sessions)
- Strategy Performance & Metrics (Win Rate %, Profit Factor, Month-over-Month)
- Empirical Backtesting & Parameter Recommendations
- Daemon Execution Gates (Skips runs on NSE holidays)
"""

import os
import json
import datetime
import logging
from typing import Tuple, List, Set, Optional
import pandas as pd

logger = logging.getLogger("HolidayManager")

# Path to the locally maintained NSE holiday calendar in GitHub
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
HOLIDAYS_JSON_PATH = os.path.join(CURRENT_DIR, "data", "nse_holidays.json")

# In-memory cached holiday set and dictionary {YYYY-MM-DD: Reason}
_CACHED_HOLIDAYS: Optional[dict] = None


def load_nse_holidays(force_reload: bool = False) -> dict:
    """
    Loads NSE trading holidays from data/nse_holidays.json.
    Returns dict of {YYYY-MM-DD: Holiday Name}.
    """
    global _CACHED_HOLIDAYS
    if _CACHED_HOLIDAYS is not None and not force_reload:
        return _CACHED_HOLIDAYS

    holidays = {}
    if os.path.exists(HOLIDAYS_JSON_PATH):
        try:
            with open(HOLIDAYS_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                holidays = data.get("holidays", {})
        except Exception as e:
            logger.warning(f"Failed to load {HOLIDAYS_JSON_PATH}: {e}")

    # Fallback safety: essential recurring national holidays if file unreadable
    if not holidays:
        holidays = {
            "2025-01-26": "Republic Day",
            "2025-03-14": "Holi",
            "2025-04-14": "Dr. Ambedkar Jayanti",
            "2025-04-18": "Good Friday",
            "2025-05-01": "Maharashtra Day",
            "2025-08-15": "Independence Day",
            "2025-10-02": "Mahatma Gandhi Jayanti",
            "2025-12-25": "Christmas",
            "2026-01-26": "Republic Day",
            "2026-08-15": "Independence Day",
            "2026-10-02": "Mahatma Gandhi Jayanti",
            "2026-12-25": "Christmas",
        }

    _CACHED_HOLIDAYS = holidays
    return _CACHED_HOLIDAYS


def is_weekend(dt: datetime.date) -> bool:
    """Returns True if the date falls on Saturday (5) or Sunday (6)."""
    return dt.weekday() >= 5


def is_nse_holiday(dt: datetime.date) -> Tuple[bool, str]:
    """
    Checks if a given date is an official NSE Trading Holiday.
    Returns (is_holiday: bool, reason: str).
    """
    holidays = load_nse_holidays()
    date_str = dt.strftime("%Y-%m-%d") if isinstance(dt, (datetime.date, datetime.datetime)) else str(dt)[:10]
    if date_str in holidays:
        return True, holidays[date_str]
    return False, ""


def is_trading_day(dt: Optional[datetime.date] = None) -> Tuple[bool, str]:
    """
    Checks if the given date is a valid active NSE trading session.
    If dt is None, uses today in IST.
    Returns (is_active: bool, reason_if_closed: str).
    """
    if dt is None:
        try:
            from zoneinfo import ZoneInfo
            dt = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).date()
        except Exception:
            dt = datetime.datetime.utcnow().date() + datetime.timedelta(hours=5, minutes=30)
    elif isinstance(dt, datetime.datetime):
        dt = dt.date()

    if is_weekend(dt):
        day_name = dt.strftime("%A")
        return False, f"Weekend market closed ({day_name})"

    is_hol, hol_name = is_nse_holiday(dt)
    if is_hol:
        return False, f"NSE Trading Holiday ({hol_name})"

    return True, "Active Trading Session"


def calculate_trading_days(start_date, end_date) -> int:
    """
    Calculates the exact number of active NSE trading sessions between start_date and end_date.
    Strictly excludes Saturdays, Sundays, and official NSE holidays.
    """
    if isinstance(start_date, str):
        try:
            start_date = datetime.datetime.strptime(start_date[:10], "%Y-%m-%d").date()
        except Exception:
            return 0
    elif isinstance(start_date, datetime.datetime):
        start_date = start_date.date()

    if isinstance(end_date, str):
        try:
            end_date = datetime.datetime.strptime(end_date[:10], "%Y-%m-%d").date()
        except Exception:
            return 0
    elif isinstance(end_date, datetime.datetime):
        end_date = end_date.date()

    if not isinstance(start_date, datetime.date) or not isinstance(end_date, datetime.date):
        return 0

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    holidays = load_nse_holidays()
    trading_days = 0
    curr = start_date + datetime.timedelta(days=1)

    while curr <= end_date:
        # Check weekday and holiday
        if curr.weekday() < 5 and curr.strftime("%Y-%m-%d") not in holidays:
            trading_days += 1
        curr += datetime.timedelta(days=1)

    return trading_days


def filter_trading_day_records(df: pd.DataFrame, timestamp_col: str = "Execution_Timestamp") -> pd.DataFrame:
    """
    Filters a DataFrame (e.g. paper trades, audit logs) to exclude records
    logged on weekends or official NSE holidays.
    Guarantees that performance metrics and empirical recommendations reflect
    only valid market session activity.
    """
    if df is None or df.empty or timestamp_col not in df.columns:
        return df

    holidays = load_nse_holidays()

    def _is_valid_row(val):
        try:
            s = str(val).strip()
            if not s or s.lower() in ["nan", "none"]:
                return True
            # Extract date portion
            d_str = s[:10]
            dt = datetime.datetime.strptime(d_str, "%Y-%m-%d").date()
            if dt.weekday() >= 5:  # Saturday or Sunday
                return False
            if d_str in holidays:   # NSE Holiday
                return False
            return True
        except Exception:
            return True

    mask = df[timestamp_col].apply(_is_valid_row)
    filtered = df[mask].copy()
    dropped_count = len(df) - len(filtered)
    if dropped_count > 0:
        logger.info(f"Filtered out {dropped_count} weekend/holiday records from {timestamp_col} for clean empirical evaluation.")
    return filtered
