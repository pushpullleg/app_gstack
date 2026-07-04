"""CSV round-trip: export, import, duplicate skip, transactional abort, name mismatch."""

from __future__ import annotations

import csv
import uuid
from datetime import date
from pathlib import Path

import pytest

from activity_logger.services.csv_io import EXPORT_COLUMNS, export_csv, import_csv


# ── helpers ───────────────────────────────────────────────────────────────────

def _setup(db):
    dept_id = db.execute("SELECT id FROM departments WHERE code='CP'").fetchone()[0]
    db.execute("INSERT INTO employees(uin,name,department_id) VALUES('U001','Alice',?)", (dept_id,))
    db.commit()
    return dept_id


def _insert_entry(db, uin="U001", entry_date="2026-07-01", hours=2.0, code="CP-01"):
    eu = str(uuid.uuid4())
    code_id = db.execute("SELECT id FROM activity_codes WHERE code=?", (code,)).fetchone()[0]
    db.execute(
        "INSERT INTO log_entries(entry_uuid,employee_uin,entry_date,hours,activity_code_id) VALUES(?,?,?,?,?)",
        (eu, uin, entry_date, hours, code_id),
    )
    db.commit()
    return eu


# ── export ────────────────────────────────────────────────────────────────────

def test_export_produces_correct_columns(db, tmp_path: Path) -> None:
    _setup(db)
    _insert_entry(db)
    out = tmp_path / "export.csv"
    count = export_csv(db, out)
    assert count == 1
    with out.open() as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == EXPORT_COLUMNS
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["uin"] == "U001"
    assert rows[0]["department_code"] == "CP"
    assert rows[0]["activity_code"] == "CP-01"


def test_export_date_range_filter(db, tmp_path: Path) -> None:
    _setup(db)
    _insert_entry(db, entry_date="2026-07-01")
    _insert_entry(db, entry_date="2026-07-15")
    _insert_entry(db, entry_date="2026-08-01")
    out = tmp_path / "range.csv"
    count = export_csv(db, out, start=date(2026, 7, 1), end=date(2026, 7, 31))
    assert count == 2


# ── round-trip (export → import to empty DB) ──────────────────────────────────

def test_round_trip_no_op(db, tmp_path: Path) -> None:
    """Exporting from db and re-importing into db is a no-op (0 inserts, N skips)."""
    _setup(db)
    _insert_entry(db)
    out = tmp_path / "rt.csv"
    export_csv(db, out)
    result = import_csv(db, out)
    assert result.inserted == 0
    assert result.skipped == 1
    assert result.errors == []


def test_round_trip_cross_machine(db, seeded_db, tmp_path: Path) -> None:
    """Import into a different install (same catalog) inserts all rows."""
    _setup(db)
    for _ in range(3):
        _insert_entry(db)
    out = tmp_path / "cross.csv"
    export_csv(db, out)
    result = import_csv(seeded_db, out)
    assert result.inserted == 3
    assert result.skipped == 0
    assert result.errors == []


# ── duplicate skip ────────────────────────────────────────────────────────────

def test_duplicate_uuid_skipped(db, seeded_db, tmp_path: Path) -> None:
    _setup(db)
    _insert_entry(db)
    out = tmp_path / "dup.csv"
    export_csv(db, out)
    # First import inserts 1.
    import_csv(seeded_db, out)
    # Second import of the same file: skip all.
    result = import_csv(seeded_db, out)
    assert result.inserted == 0
    assert result.skipped == 1


# ── transactional abort on bad row ────────────────────────────────────────────

def test_import_aborts_on_unknown_activity_code(db, empty_db, tmp_path: Path) -> None:
    _setup(db)
    _insert_entry(db)
    out = tmp_path / "bad.csv"
    export_csv(db, out)
    # Corrupt one row.
    with out.open("r") as f:
        content = f.read()
    content = content.replace("CP-01", "BADCODE")
    with out.open("w") as f:
        f.write(content)
    result = import_csv(empty_db, out)
    assert len(result.errors) >= 1
    assert result.inserted == 0
    # No partial writes.
    count = empty_db.execute("SELECT COUNT(*) FROM log_entries").fetchone()[0]
    assert count == 0


def test_import_aborts_on_unknown_department(db, empty_db, tmp_path: Path) -> None:
    _setup(db)
    _insert_entry(db)
    out = tmp_path / "baddept.csv"
    export_csv(db, out)
    with out.open("r") as f:
        content = f.read()
    content = content.replace(",CP,", ",XXXX,")
    with out.open("w") as f:
        f.write(content)
    result = import_csv(empty_db, out)
    assert any("department" in e.lower() for e in result.errors)


def test_import_aborts_on_bad_hours(db, empty_db, tmp_path: Path) -> None:
    bad_csv = tmp_path / "badhours.csv"
    with bad_csv.open("w") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerow({
            "entry_uuid": str(uuid.uuid4()),
            "uin": "U001",
            "employee_name": "Alice",
            "department_code": "CP",
            "activity_code": "CP-01",
            "entry_date": "2026-07-01",
            "hours": "0",
            "description": "",
            "created_at": "2026-07-01 09:00:00",
        })
    result = import_csv(empty_db, bad_csv)
    assert any("hours" in e.lower() for e in result.errors)


# ── created_at preserved ──────────────────────────────────────────────────────

def test_import_preserves_created_at(db, seeded_db, tmp_path: Path) -> None:
    _setup(db)
    _insert_entry(db)
    out = tmp_path / "ts.csv"
    export_csv(db, out)
    with out.open("r") as f:
        reader = csv.DictReader(f)
        original_created_at = list(reader)[0]["created_at"]
    import_csv(seeded_db, out)
    imported = seeded_db.execute("SELECT created_at FROM log_entries").fetchone()[0]
    assert imported == original_created_at


# ── name mismatch reported ────────────────────────────────────────────────────

def test_name_mismatch_reported(db, seeded_db, tmp_path: Path) -> None:
    _setup(db)
    _insert_entry(db)
    out = tmp_path / "name.csv"
    export_csv(db, out)
    # Plant the employee in seeded_db with a different name.
    dept_id = seeded_db.execute("SELECT id FROM departments WHERE code='CP'").fetchone()[0]
    seeded_db.execute("INSERT INTO employees(uin,name,department_id) VALUES('U001','Wrong Name',?)", (dept_id,))
    seeded_db.commit()
    result = import_csv(seeded_db, out)
    assert len(result.name_mismatches) == 1
    assert result.name_mismatches[0][0] == "U001"


# ── home dept = latest entry_date dept ───────────────────────────────────────

def test_new_employee_home_dept_from_latest_row(db, seeded_db, tmp_path: Path) -> None:
    """New employee's home dept = the dept of their most recent entry_date row."""
    dept_cp = db.execute("SELECT id FROM departments WHERE code='CP'").fetchone()[0]
    db.execute("INSERT INTO employees(uin,name,department_id) VALUES('U002','Bob',?)", (dept_cp,))
    db.commit()

    cp1 = db.execute("SELECT id FROM activity_codes WHERE code='CP-01'").fetchone()[0]
    mmc1 = db.execute("SELECT id FROM activity_codes WHERE code='MMC-01'").fetchone()[0]
    # Older entry: CP dept.
    db.execute(
        "INSERT INTO log_entries(entry_uuid,employee_uin,entry_date,hours,activity_code_id) VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()), "U002", "2026-07-01", 1.0, cp1),
    )
    # Newer entry: MMC dept.
    db.execute(
        "INSERT INTO log_entries(entry_uuid,employee_uin,entry_date,hours,activity_code_id) VALUES(?,?,?,?,?)",
        (str(uuid.uuid4()), "U002", "2026-07-15", 2.0, mmc1),
    )
    db.commit()

    out = tmp_path / "homedept.csv"
    export_csv(db, out)
    import_csv(seeded_db, out)

    emp = seeded_db.execute("SELECT department_id FROM employees WHERE uin='U002'").fetchone()
    assert emp is not None
    dept_code = seeded_db.execute("SELECT code FROM departments WHERE id=?", (emp[0],)).fetchone()[0]
    assert dept_code == "MMC"
