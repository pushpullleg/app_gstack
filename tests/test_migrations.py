"""Migration correctness: schema reaches target version; re-running is a no-op."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from activity_logger.db import connection, migrations, seed


def test_schema_reaches_latest_version(tmp_path: Path) -> None:
    conn = connection.connect(tmp_path / "m.db")
    migrations.migrate(conn)
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == 1


def test_migration_idempotent(tmp_path: Path) -> None:
    conn = connection.connect(tmp_path / "m.db")
    migrations.migrate(conn)
    migrations.migrate(conn)  # second call must not raise
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == 1


def test_log_entries_has_entry_uuid_column(tmp_path: Path) -> None:
    conn = connection.connect(tmp_path / "m.db")
    migrations.migrate(conn)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(log_entries)")}
    assert "entry_uuid" in cols


def test_generated_reports_table_exists(tmp_path: Path) -> None:
    conn = connection.connect(tmp_path / "m.db")
    migrations.migrate(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "generated_reports" in tables


def test_foreign_keys_enforced(tmp_path: Path) -> None:
    conn = connection.connect(tmp_path / "m.db")
    migrations.migrate(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO employees(uin, name, department_id) VALUES('X','Y',9999)"
        )
        conn.commit()


def test_seed_loads(tmp_path: Path) -> None:
    conn = connection.connect(tmp_path / "s.db")
    migrations.migrate(conn)
    seed.seed(conn)
    dept_count = conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0]
    code_count = conn.execute("SELECT COUNT(*) FROM activity_codes").fetchone()[0]
    assert dept_count == 3
    assert code_count == 9


def test_seed_idempotent(tmp_path: Path) -> None:
    conn = connection.connect(tmp_path / "s.db")
    migrations.migrate(conn)
    seed.seed(conn)
    seed.seed(conn)
    dept_count = conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0]
    assert dept_count == 3


def test_hours_check_constraint_rejects_zero(db: sqlite3.Connection) -> None:
    """hours > 0 is enforced at the DB level."""
    dept_id = db.execute("SELECT id FROM departments WHERE code='CP'").fetchone()[0]
    db.execute("INSERT INTO employees(uin, name, department_id) VALUES('U1','Test User', ?)", (dept_id,))
    code_id = db.execute("SELECT id FROM activity_codes WHERE code='CP-01'").fetchone()[0]
    import uuid
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO log_entries(entry_uuid,employee_uin,entry_date,hours,activity_code_id)"
            " VALUES(?,?,?,?,?)",
            (str(uuid.uuid4()), "U1", "2026-07-01", 0.0, code_id),
        )
        db.commit()


def test_hours_check_constraint_rejects_over_24(db: sqlite3.Connection) -> None:
    dept_id = db.execute("SELECT id FROM departments WHERE code='CP'").fetchone()[0]
    db.execute("INSERT OR IGNORE INTO employees(uin, name, department_id) VALUES('U2','User2', ?)", (dept_id,))
    code_id = db.execute("SELECT id FROM activity_codes WHERE code='CP-01'").fetchone()[0]
    import uuid
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO log_entries(entry_uuid,employee_uin,entry_date,hours,activity_code_id)"
            " VALUES(?,?,?,?,?)",
            (str(uuid.uuid4()), "U2", "2026-07-01", 24.5, code_id),
        )
        db.commit()
