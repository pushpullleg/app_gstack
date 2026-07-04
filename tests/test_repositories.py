"""Repository CRUD correctness."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date

import pytest

from activity_logger.repositories.activity_codes import ActivityCodeRepo
from activity_logger.repositories.departments import DepartmentRepo
from activity_logger.repositories.employees import EmployeeRepo
from activity_logger.repositories.generated_reports import GeneratedReportRepo
from activity_logger.repositories.log_entries import LogEntryRepo


# ── helpers ──────────────────────────────────────────────────────────────────

def _insert_employee(db: sqlite3.Connection, uin: str = "U001", name: str = "Test User") -> int:
    dept_id = db.execute("SELECT id FROM departments WHERE code='CP'").fetchone()[0]
    EmployeeRepo(db).upsert(uin, name, dept_id)
    db.commit()
    return dept_id


def _cp01_id(db: sqlite3.Connection) -> int:
    return db.execute("SELECT id FROM activity_codes WHERE code='CP-01'").fetchone()[0]


# ── DepartmentRepo ────────────────────────────────────────────────────────────

def test_list_active_returns_three_seeded_depts(db: sqlite3.Connection) -> None:
    repo = DepartmentRepo(db)
    depts = repo.list_active()
    codes = {d.code for d in depts}
    assert codes == {"CP", "MMC", "ADV"}


def test_get_by_code_found(db: sqlite3.Connection) -> None:
    dept = DepartmentRepo(db).get_by_code("CP")
    assert dept is not None
    assert dept.code == "CP"


def test_get_by_code_not_found(db: sqlite3.Connection) -> None:
    assert DepartmentRepo(db).get_by_code("NOPE") is None


# ── ActivityCodeRepo ──────────────────────────────────────────────────────────

def test_list_by_department_filters_correctly(db: sqlite3.Connection) -> None:
    dept = DepartmentRepo(db).get_by_code("CP")
    codes = ActivityCodeRepo(db).list_by_department(dept.id)
    assert len(codes) == 3
    assert all(c.code.startswith("CP-") for c in codes)


def test_get_by_code_returns_correct_record(db: sqlite3.Connection) -> None:
    code = ActivityCodeRepo(db).get_by_code("MMC-01")
    assert code is not None
    assert code.code == "MMC-01"


def test_get_by_id_round_trip(db: sqlite3.Connection) -> None:
    code = ActivityCodeRepo(db).get_by_code("ADV-02")
    assert code is not None
    same = ActivityCodeRepo(db).get_by_id(code.id)
    assert same == code


# ── EmployeeRepo ──────────────────────────────────────────────────────────────

def test_upsert_inserts_new_employee(db: sqlite3.Connection) -> None:
    _insert_employee(db)
    emp = EmployeeRepo(db).get_by_uin("U001")
    assert emp is not None
    assert emp.name == "Test User"


def test_upsert_updates_existing_employee(db: sqlite3.Connection) -> None:
    _insert_employee(db)
    dept_id = db.execute("SELECT id FROM departments WHERE code='CP'").fetchone()[0]
    EmployeeRepo(db).upsert("U001", "Updated Name", dept_id)
    db.commit()
    emp = EmployeeRepo(db).get_by_uin("U001")
    assert emp.name == "Updated Name"


def test_uin_case_preserved(db: sqlite3.Connection) -> None:
    """Exact case is stored; 'a-001' and 'A-001' are different records."""
    dept_id = db.execute("SELECT id FROM departments WHERE code='CP'").fetchone()[0]
    repo = EmployeeRepo(db)
    repo.upsert("a-001", "Lower User", dept_id)
    db.commit()
    assert repo.get_by_uin("A-001") is None
    assert repo.get_by_uin("a-001") is not None


def test_search_prefix_match(db: sqlite3.Connection) -> None:
    _insert_employee(db, "U002", "Alpha Employee")
    _insert_employee(db, "U003", "Beta Employee")
    results = EmployeeRepo(db).search("Alpha")
    assert any(e.name == "Alpha Employee" for e in results)


# ── LogEntryRepo ──────────────────────────────────────────────────────────────

def test_insert_and_get_by_uuid(db: sqlite3.Connection) -> None:
    _insert_employee(db)
    code_id = _cp01_id(db)
    repo = LogEntryRepo(db)
    eu = str(uuid.uuid4())
    row_id = repo.insert(eu, "U001", date(2026, 7, 1), 3.0, code_id, "Test entry")
    db.commit()
    entry = repo.get_by_uuid(eu)
    assert entry is not None
    assert entry.hours == 3.0
    assert entry.entry_date == date(2026, 7, 1)


def test_entry_uuid_unique_constraint(db: sqlite3.Connection) -> None:
    _insert_employee(db)
    code_id = _cp01_id(db)
    eu = str(uuid.uuid4())
    LogEntryRepo(db).insert(eu, "U001", date(2026, 7, 1), 1.0, code_id, "")
    db.commit()
    with pytest.raises(sqlite3.IntegrityError):
        LogEntryRepo(db).insert(eu, "U001", date(2026, 7, 2), 2.0, code_id, "")
        db.commit()


def test_get_by_date(db: sqlite3.Connection) -> None:
    _insert_employee(db)
    code_id = _cp01_id(db)
    repo = LogEntryRepo(db)
    d = date(2026, 7, 4)
    repo.insert(str(uuid.uuid4()), "U001", d, 2.0, code_id, "A")
    repo.insert(str(uuid.uuid4()), "U001", d, 1.5, code_id, "B")
    repo.insert(str(uuid.uuid4()), "U001", date(2026, 7, 5), 3.0, code_id, "C")
    db.commit()
    entries = repo.get_by_date(d)
    assert len(entries) == 2


def test_get_by_period(db: sqlite3.Connection) -> None:
    _insert_employee(db)
    code_id = _cp01_id(db)
    repo = LogEntryRepo(db)
    repo.insert(str(uuid.uuid4()), "U001", date(2026, 7, 1), 1.0, code_id, "")
    repo.insert(str(uuid.uuid4()), "U001", date(2026, 9, 30), 2.0, code_id, "")
    repo.insert(str(uuid.uuid4()), "U001", date(2026, 10, 1), 3.0, code_id, "")
    db.commit()
    entries = repo.get_by_period("U001", date(2026, 7, 1), date(2026, 9, 30))
    assert len(entries) == 2
    assert all(e.employee_uin == "U001" for e in entries)


def test_update_entry(db: sqlite3.Connection) -> None:
    _insert_employee(db)
    code_id = _cp01_id(db)
    repo = LogEntryRepo(db)
    eu = str(uuid.uuid4())
    repo.insert(eu, "U001", date(2026, 7, 1), 1.0, code_id, "Original")
    db.commit()
    entry = repo.get_by_uuid(eu)
    repo.update(entry.id, 4.5, code_id, "Updated")
    db.commit()
    updated = repo.get_by_uuid(eu)
    assert updated.hours == 4.5
    assert updated.description == "Updated"
    assert updated.updated_at is not None


def test_delete_entry(db: sqlite3.Connection) -> None:
    _insert_employee(db)
    code_id = _cp01_id(db)
    repo = LogEntryRepo(db)
    eu = str(uuid.uuid4())
    repo.insert(eu, "U001", date(2026, 7, 1), 1.0, code_id, "")
    db.commit()
    entry = repo.get_by_uuid(eu)
    repo.delete(entry.id)
    db.commit()
    assert repo.get_by_uuid(eu) is None


def test_count(db: sqlite3.Connection) -> None:
    _insert_employee(db)
    code_id = _cp01_id(db)
    repo = LogEntryRepo(db)
    assert repo.count() == 0
    repo.insert(str(uuid.uuid4()), "U001", date(2026, 7, 1), 1.0, code_id, "")
    db.commit()
    assert repo.count() == 1


# ── GeneratedReportRepo ───────────────────────────────────────────────────────

def test_insert_and_get_latest(db: sqlite3.Connection) -> None:
    _insert_employee(db)
    repo = GeneratedReportRepo(db)
    repo.insert("U001", "2026-07-01", "2026-09-30", "calendar", "/tmp/r.pdf", "abc123")
    db.commit()
    report = repo.get_latest("U001", "2026-07-01", "2026-09-30")
    assert report is not None
    assert report.data_hash == "abc123"


def test_get_latest_returns_most_recent(db: sqlite3.Connection) -> None:
    _insert_employee(db)
    repo = GeneratedReportRepo(db)
    repo.insert("U001", "2026-07-01", "2026-09-30", "calendar", "/tmp/r1.pdf", "hash1")
    db.commit()
    # Simulate a later generation (updated_at drift).
    repo.insert("U001", "2026-07-01", "2026-09-30", "calendar", "/tmp/r2.pdf", "hash2")
    db.commit()
    report = repo.get_latest("U001", "2026-07-01", "2026-09-30")
    assert report.data_hash == "hash2"


def test_get_latest_returns_none_for_unknown_period(db: sqlite3.Connection) -> None:
    _insert_employee(db)
    assert GeneratedReportRepo(db).get_latest("U001", "2025-01-01", "2025-03-31") is None
