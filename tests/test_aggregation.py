"""Aggregation: totals math, empty quarter, monthly rows."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from activity_logger.services.aggregation_service import AggregationService
from activity_logger.services.periods import DateRange


def _setup(db):
    dept_id = db.execute("SELECT id FROM departments WHERE code='CP'").fetchone()[0]
    db.execute("INSERT INTO employees(uin, name, department_id) VALUES('U001','Alice', ?)", (dept_id,))
    db.commit()
    return dept_id


def _cp01(db):
    return db.execute("SELECT id FROM activity_codes WHERE code='CP-01'").fetchone()[0]


def _cp02(db):
    return db.execute("SELECT id FROM activity_codes WHERE code='CP-02'").fetchone()[0]


def test_quarterly_totals_sum(db) -> None:
    _setup(db)
    cp1 = _cp01(db)
    cp2 = _cp02(db)
    db.execute(
        "INSERT INTO log_entries(entry_uuid,employee_uin,entry_date,hours,activity_code_id) VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()), "U001", "2026-07-01", 3.0, cp1),
    )
    db.execute(
        "INSERT INTO log_entries(entry_uuid,employee_uin,entry_date,hours,activity_code_id) VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()), "U001", "2026-07-02", 1.5, cp1),
    )
    db.execute(
        "INSERT INTO log_entries(entry_uuid,employee_uin,entry_date,hours,activity_code_id) VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()), "U001", "2026-07-05", 4.0, cp2),
    )
    db.commit()

    svc = AggregationService(db)
    rows = svc.quarterly_totals("U001", DateRange(date(2026, 7, 1), date(2026, 9, 30)))
    totals = {r.code: r.hours for r in rows}

    assert totals["CP-01"] == 4.5
    assert totals["CP-02"] == 4.0
    assert sum(totals.values()) == 8.5


def test_quarterly_totals_grand_total_equals_sum(db) -> None:
    _setup(db)
    cp1 = _cp01(db)
    for h in [1.25, 2.75, 3.0]:
        db.execute(
            "INSERT INTO log_entries(entry_uuid,employee_uin,entry_date,hours,activity_code_id) VALUES(?,?,?,?,?)",
            (str(uuid.uuid4()), "U001", "2026-08-15", h, cp1),
        )
    db.commit()
    svc = AggregationService(db)
    rows = svc.quarterly_totals("U001", DateRange(date(2026, 7, 1), date(2026, 9, 30)))
    grand_total = sum(r.hours for r in rows)
    assert grand_total == 7.0


def test_empty_quarter_returns_empty_list(db) -> None:
    _setup(db)
    svc = AggregationService(db)
    rows = svc.quarterly_totals("U001", DateRange(date(2026, 1, 1), date(2026, 3, 31)))
    assert rows == []


def test_quarterly_excludes_out_of_range(db) -> None:
    _setup(db)
    cp1 = _cp01(db)
    # Entry outside Q3 (Oct 1 = Q4).
    db.execute(
        "INSERT INTO log_entries(entry_uuid,employee_uin,entry_date,hours,activity_code_id) VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()), "U001", "2026-10-01", 5.0, cp1),
    )
    # Entry on Q3 boundary (Sep 30).
    db.execute(
        "INSERT INTO log_entries(entry_uuid,employee_uin,entry_date,hours,activity_code_id) VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()), "U001", "2026-09-30", 2.0, cp1),
    )
    db.commit()
    svc = AggregationService(db)
    rows = svc.quarterly_totals("U001", DateRange(date(2026, 7, 1), date(2026, 9, 30)))
    assert sum(r.hours for r in rows) == 2.0


def test_monthly_rows_filtered_to_month(db) -> None:
    _setup(db)
    cp1 = _cp01(db)
    db.execute(
        "INSERT INTO log_entries(entry_uuid,employee_uin,entry_date,hours,activity_code_id) VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()), "U001", "2026-07-15", 2.0, cp1),
    )
    db.execute(
        "INSERT INTO log_entries(entry_uuid,employee_uin,entry_date,hours,activity_code_id) VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()), "U001", "2026-08-01", 3.0, cp1),
    )
    db.commit()
    svc = AggregationService(db)
    rows = svc.monthly_rows(2026, 7)
    assert len(rows) == 1
    assert rows[0].hours == 2.0
