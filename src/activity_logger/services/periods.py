"""Quarter and month date-range math — calendar quarters and federal fiscal quarters.

Calendar: Q1=Jan–Mar, Q2=Apr–Jun, Q3=Jul–Sep, Q4=Oct–Dec.
Federal fiscal: Q1=Oct–Dec, Q2=Jan–Mar, Q3=Apr–Jun, Q4=Jul–Sep (FY starts Oct 1).
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DateRange:
    start: date   # inclusive
    end: date     # inclusive


def _last_day_of_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


# ── Calendar quarters ─────────────────────────────────────────────────────────

_CALENDAR_QUARTER_MONTHS = {
    1: (1, 3),   # Q1: Jan–Mar
    2: (4, 6),   # Q2: Apr–Jun
    3: (7, 9),   # Q3: Jul–Sep
    4: (10, 12), # Q4: Oct–Dec
}


def calendar_quarter_of(d: date) -> tuple[int, int]:
    """Return (year, quarter_number) for a calendar quarter."""
    for q, (start_m, end_m) in _CALENDAR_QUARTER_MONTHS.items():
        if start_m <= d.month <= end_m:
            return d.year, q
    raise ValueError(f"Cannot determine calendar quarter for {d}")  # unreachable


def calendar_quarter_range(year: int, quarter: int) -> DateRange:
    start_m, end_m = _CALENDAR_QUARTER_MONTHS[quarter]
    start = date(year, start_m, 1)
    end = date(year, end_m, _last_day_of_month(year, end_m))
    return DateRange(start=start, end=end)


def calendar_quarter_label(year: int, quarter: int) -> str:
    return f"Q{quarter} {year}"


# ── Federal fiscal quarters ───────────────────────────────────────────────────
# FY N starts Oct 1 of calendar year N-1 and ends Sep 30 of calendar year N.
# FY Q1: Oct–Dec (calendar year N-1), FY Q2: Jan–Mar (N), FY Q3: Apr–Jun (N), FY Q4: Jul–Sep (N).

def federal_fiscal_year_of(d: date) -> int:
    """Federal fiscal year: Oct 1 starts new FY."""
    return d.year + 1 if d.month >= 10 else d.year


def federal_fiscal_quarter_of(d: date) -> tuple[int, int]:
    """Return (fiscal_year, quarter_number) for the federal fiscal calendar."""
    fy = federal_fiscal_year_of(d)
    if d.month >= 10:
        return fy, 1
    elif d.month <= 3:
        return fy, 2
    elif d.month <= 6:
        return fy, 3
    else:
        return fy, 4


def federal_fiscal_quarter_range(fiscal_year: int, quarter: int) -> DateRange:
    if quarter == 1:
        start = date(fiscal_year - 1, 10, 1)
        end = date(fiscal_year - 1, 12, 31)
    elif quarter == 2:
        start = date(fiscal_year, 1, 1)
        end = date(fiscal_year, 3, _last_day_of_month(fiscal_year, 3))
    elif quarter == 3:
        start = date(fiscal_year, 4, 1)
        end = date(fiscal_year, 6, 30)
    elif quarter == 4:
        start = date(fiscal_year, 7, 1)
        end = date(fiscal_year, 9, 30)
    else:
        raise ValueError(f"Invalid quarter: {quarter}")
    return DateRange(start=start, end=end)


def federal_fiscal_quarter_label(fiscal_year: int, quarter: int) -> str:
    return f"FY{fiscal_year % 100:02d} Q{quarter}"


# ── Unified interface ─────────────────────────────────────────────────────────

def quarter_range(scheme: str, year: int, quarter: int) -> DateRange:
    if scheme == "calendar":
        return calendar_quarter_range(year, quarter)
    elif scheme == "federal_fiscal":
        return federal_fiscal_quarter_range(year, quarter)
    raise ValueError(f"Unknown quarter scheme: {scheme!r}")


def quarter_of(scheme: str, d: date) -> tuple[int, int]:
    """Return (year_or_fiscal_year, quarter) for the given date and scheme."""
    if scheme == "calendar":
        return calendar_quarter_of(d)
    elif scheme == "federal_fiscal":
        return federal_fiscal_quarter_of(d)
    raise ValueError(f"Unknown quarter scheme: {scheme!r}")


def quarter_label(scheme: str, year: int, quarter: int) -> str:
    if scheme == "calendar":
        return calendar_quarter_label(year, quarter)
    elif scheme == "federal_fiscal":
        return federal_fiscal_quarter_label(year, quarter)
    raise ValueError(f"Unknown quarter scheme: {scheme!r}")


def month_range(year: int, month: int) -> DateRange:
    start = date(year, month, 1)
    end = date(year, month, _last_day_of_month(year, month))
    return DateRange(start=start, end=end)
