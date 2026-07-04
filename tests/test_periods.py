"""Period math: quarter boundaries, fiscal mode, leap day, boundary dates."""

from __future__ import annotations

from datetime import date

from activity_logger.services.periods import (
    calendar_quarter_of,
    calendar_quarter_range,
    federal_fiscal_quarter_of,
    federal_fiscal_quarter_range,
    federal_fiscal_year_of,
    month_range,
    quarter_label,
    quarter_of,
    quarter_range,
)


# ── Calendar quarters ─────────────────────────────────────────────────────────

def test_calendar_quarter_of_q1() -> None:
    assert calendar_quarter_of(date(2026, 1, 1)) == (2026, 1)
    assert calendar_quarter_of(date(2026, 3, 31)) == (2026, 1)


def test_calendar_quarter_of_q3() -> None:
    assert calendar_quarter_of(date(2026, 7, 1)) == (2026, 3)
    assert calendar_quarter_of(date(2026, 9, 30)) == (2026, 3)


def test_calendar_quarter_of_q4() -> None:
    assert calendar_quarter_of(date(2026, 10, 1)) == (2026, 4)
    assert calendar_quarter_of(date(2026, 12, 31)) == (2026, 4)


def test_calendar_q3_range() -> None:
    r = calendar_quarter_range(2026, 3)
    assert r.start == date(2026, 7, 1)
    assert r.end == date(2026, 9, 30)


def test_calendar_q1_range() -> None:
    r = calendar_quarter_range(2026, 1)
    assert r.start == date(2026, 1, 1)
    assert r.end == date(2026, 3, 31)


def test_calendar_q4_range() -> None:
    r = calendar_quarter_range(2026, 4)
    assert r.start == date(2026, 10, 1)
    assert r.end == date(2026, 12, 31)


# Critical boundary: Sep 30 is Q3-end; Oct 1 is Q4-start.
def test_calendar_boundary_sep30_is_q3() -> None:
    assert calendar_quarter_of(date(2026, 9, 30)) == (2026, 3)


def test_calendar_boundary_oct1_is_q4() -> None:
    assert calendar_quarter_of(date(2026, 10, 1)) == (2026, 4)


def test_calendar_boundary_dec31_is_q4() -> None:
    assert calendar_quarter_of(date(2026, 12, 31)) == (2026, 4)


def test_calendar_boundary_jan1_is_q1_next_year() -> None:
    assert calendar_quarter_of(date(2027, 1, 1)) == (2027, 1)


# ── Federal fiscal quarters ───────────────────────────────────────────────────

def test_federal_fiscal_year_of_oct() -> None:
    # Oct 1 2025 begins FY2026.
    assert federal_fiscal_year_of(date(2025, 10, 1)) == 2026


def test_federal_fiscal_year_of_sep() -> None:
    # Sep 30 2026 is still FY2026.
    assert federal_fiscal_year_of(date(2026, 9, 30)) == 2026


def test_federal_fy_q1_is_oct_dec() -> None:
    r = federal_fiscal_quarter_range(2026, 1)
    assert r.start == date(2025, 10, 1)
    assert r.end == date(2025, 12, 31)


def test_federal_fy_q2_is_jan_mar() -> None:
    r = federal_fiscal_quarter_range(2026, 2)
    assert r.start == date(2026, 1, 1)
    assert r.end == date(2026, 3, 31)


def test_federal_fy_q3_is_apr_jun() -> None:
    r = federal_fiscal_quarter_range(2026, 3)
    assert r.start == date(2026, 4, 1)
    assert r.end == date(2026, 6, 30)


def test_federal_fy_q4_is_jul_sep() -> None:
    r = federal_fiscal_quarter_range(2026, 4)
    assert r.start == date(2026, 7, 1)
    assert r.end == date(2026, 9, 30)


def test_federal_quarter_of_oct1() -> None:
    # Oct 1 2025 → FY2026 Q1.
    assert federal_fiscal_quarter_of(date(2025, 10, 1)) == (2026, 1)


def test_federal_quarter_of_sep30() -> None:
    # Sep 30 2026 → FY2026 Q4.
    assert federal_fiscal_quarter_of(date(2026, 9, 30)) == (2026, 4)


# ── Leap day ─────────────────────────────────────────────────────────────────

def test_leap_day_q1() -> None:
    assert calendar_quarter_of(date(2028, 2, 29)) == (2028, 1)


def test_leap_year_q1_range() -> None:
    r = calendar_quarter_range(2028, 1)
    assert r.end == date(2028, 3, 31)


# ── Unified API ──────────────────────────────────────────────────────────────

def test_quarter_range_calendar() -> None:
    r = quarter_range("calendar", 2026, 3)
    assert r.start == date(2026, 7, 1)


def test_quarter_range_fiscal() -> None:
    r = quarter_range("federal_fiscal", 2026, 1)
    assert r.start == date(2025, 10, 1)


def test_quarter_label_calendar() -> None:
    assert quarter_label("calendar", 2026, 3) == "Q3 2026"


def test_quarter_label_fiscal() -> None:
    assert quarter_label("federal_fiscal", 2026, 3) == "FY26 Q3"


# ── Month range ───────────────────────────────────────────────────────────────

def test_month_range_july() -> None:
    r = month_range(2026, 7)
    assert r.start == date(2026, 7, 1)
    assert r.end == date(2026, 7, 31)


def test_month_range_february_non_leap() -> None:
    r = month_range(2026, 2)
    assert r.end == date(2026, 2, 28)


def test_month_range_february_leap() -> None:
    r = month_range(2028, 2)
    assert r.end == date(2028, 2, 29)
