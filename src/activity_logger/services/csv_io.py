"""CSV export and UUID-keyed transactional import.

Export columns: entry_uuid, uin, employee_name, department_code, activity_code,
                entry_date, hours, description, created_at

Import semantics:
- Rows matched by entry_uuid: existing → skip (counted), new → insert.
- All-or-nothing: validation runs against every row before any write.
- created_at from the CSV is preserved on import.
- New employee's home dept = department of their latest entry_date row.
- UIN arriving with a different name → reported, not silently renamed.
- Employee records upserted by UIN on import (insert or ignore; name mismatch reported).
"""

from __future__ import annotations

import csv
import io
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from activity_logger.repositories.activity_codes import ActivityCodeRepo
from activity_logger.repositories.departments import DepartmentRepo
from activity_logger.repositories.employees import EmployeeRepo
from activity_logger.repositories.log_entries import LogEntryRepo

EXPORT_COLUMNS = [
    "entry_uuid", "uin", "employee_name", "department_code",
    "activity_code", "entry_date", "hours", "description", "created_at",
]


@dataclass(frozen=True)
class ImportResult:
    inserted: int
    skipped: int
    name_mismatches: list[tuple[str, str, str]]  # (uin, csv_name, db_name)
    errors: list[str]


def export_csv(conn: sqlite3.Connection, out_path: Path, start: date | None = None, end: date | None = None) -> int:
    """Write all (or date-range) entries to a CSV file. Returns row count."""
    where = ""
    params: list = []
    if start and end:
        where = "WHERE l.entry_date >= ? AND l.entry_date <= ?"
        params = [start.isoformat(), end.isoformat()]
    elif start:
        where = "WHERE l.entry_date >= ?"
        params = [start.isoformat()]
    elif end:
        where = "WHERE l.entry_date <= ?"
        params = [end.isoformat()]

    rows = conn.execute(
        f"""
        SELECT l.entry_uuid, l.employee_uin AS uin, e.name AS employee_name,
               d.code AS department_code, ac.code AS activity_code,
               l.entry_date, l.hours, l.description, l.created_at
        FROM log_entries l
        JOIN employees e ON e.uin = l.employee_uin
        JOIN activity_codes ac ON ac.id = l.activity_code_id
        JOIN departments d ON d.id = ac.department_id
        {where}
        ORDER BY l.entry_date, l.employee_uin, ac.code
        """,
        params,
    ).fetchall()

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow(dict(r))

    return len(rows)


def import_csv(conn: sqlite3.Connection, csv_path: Path) -> ImportResult:
    """Transactional import. Validates all rows first; writes none on any error."""
    dept_repo = DepartmentRepo(conn)
    code_repo = ActivityCodeRepo(conn)
    emp_repo = EmployeeRepo(conn)
    log_repo = LogEntryRepo(conn)

    dept_by_code = {d.code: d for d in dept_repo.list_active()}
    code_by_code = {c.code: c for c in code_repo.list_all_active()}

    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # ── Validation pass (no DB writes) ────────────────────────────────────────
    errors: list[str] = []
    for i, row in enumerate(rows, start=2):
        line = f"Row {i}"
        if row.get("department_code", "") not in dept_by_code:
            errors.append(f"{line}: unknown department_code '{row.get('department_code')}'")
        if row.get("activity_code", "") not in code_by_code:
            errors.append(f"{line}: unknown activity_code '{row.get('activity_code')}'")
        try:
            hours = float(row.get("hours", 0))
            if hours <= 0 or hours > 24:
                errors.append(f"{line}: hours must be > 0 and ≤ 24 (got {hours})")
        except (ValueError, TypeError):
            errors.append(f"{line}: hours is not a number")
        try:
            date.fromisoformat(row.get("entry_date", ""))
        except ValueError:
            errors.append(f"{line}: invalid entry_date '{row.get('entry_date')}'")
        if not row.get("entry_uuid", "").strip():
            errors.append(f"{line}: missing entry_uuid")

    if errors:
        return ImportResult(inserted=0, skipped=0, name_mismatches=[], errors=errors)

    # ── Write pass (single transaction) ──────────────────────────────────────
    inserted = 0
    skipped = 0
    name_mismatches: list[tuple[str, str, str]] = []

    # Group rows by UIN to find home dept (latest entry_date per new employee).
    uin_latest: dict[str, tuple[date, str]] = {}
    for row in rows:
        uin = row["uin"]
        entry_date = date.fromisoformat(row["entry_date"])
        dept_code = row["department_code"]
        prev = uin_latest.get(uin)
        if prev is None or entry_date > prev[0] or (entry_date == prev[0]):
            uin_latest[uin] = (entry_date, dept_code)

    try:
        for row in rows:
            uin = row["uin"]
            entry_uuid = row["entry_uuid"]
            csv_name = row["employee_name"]

            # Skip if UUID already in DB.
            if log_repo.get_by_uuid(entry_uuid) is not None:
                skipped += 1
                continue

            # Upsert employee (insert if new, leave existing alone).
            existing_emp = emp_repo.get_by_uin(uin)
            if existing_emp is None:
                home_dept_code = uin_latest[uin][1]
                dept_id = dept_by_code[home_dept_code].id
                emp_repo.upsert(uin, csv_name, dept_id)
            elif existing_emp.name != csv_name:
                name_mismatches.append((uin, csv_name, existing_emp.name))

            code = code_by_code[row["activity_code"]]
            log_repo.insert(
                entry_uuid=entry_uuid,
                employee_uin=uin,
                entry_date=date.fromisoformat(row["entry_date"]),
                hours=float(row["hours"]),
                activity_code_id=code.id,
                description=row.get("description", ""),
                created_at=row.get("created_at") or None,
            )
            inserted += 1

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return ImportResult(inserted=inserted, skipped=skipped, name_mismatches=name_mismatches, errors=[])
