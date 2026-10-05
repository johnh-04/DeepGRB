"""
Explicit, inclusive analysis windows.

All dates are UTC calendar days in ISO format ('YYYY-MM-DD'). A window
[start, end] includes every instant of both the start and the end day.
"""

from typing import List

import pandas as pd


def _day(date: str) -> pd.Timestamp:
    return pd.Timestamp(date).normalize()


def window_days(start_date: str, end_date: str) -> List[str]:
    """Returns every day of the inclusive window as 'YYMMDD' (Fermi file naming)."""
    start, end = _day(start_date), _day(end_date)
    if end < start:
        raise ValueError(f"End date {end_date} precedes start date {start_date}")
    return [d.strftime("%y%m%d") for d in pd.date_range(start, end, freq="D")]


def in_window(times: pd.Series, start_date: str, end_date: str) -> pd.Series:
    """Boolean mask of UTC timestamps falling inside the inclusive window; missing times are outside."""
    t = pd.to_datetime(pd.Series(times), errors="coerce")
    return (t >= _day(start_date)) & (t < _day(end_date) + pd.Timedelta(days=1))


def days_with_data(timestamps: pd.Series, start_date: str, end_date: str) -> List[str]:
    """Sorted distinct days ('YYYY-MM-DD') inside the window that have at least one timestamp."""
    t = pd.to_datetime(pd.Series(timestamps), errors="coerce")
    t = t[in_window(t, start_date, end_date)]
    return sorted(t.dt.strftime("%Y-%m-%d").unique().tolist())
