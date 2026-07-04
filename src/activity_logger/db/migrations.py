"""Forward-only numbered migrations via PRAGMA user_version."""

from __future__ import annotations

import sqlite3

_MIGRATIONS: list[str] = [
    # Migration 1 — initial schema
    """
    CREATE TABLE departments (
        id      INTEGER PRIMARY KEY,
        code    TEXT NOT NULL UNIQUE,
        name    TEXT NOT NULL,
        active  INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE activity_codes (
        id            INTEGER PRIMARY KEY,
        department_id INTEGER NOT NULL REFERENCES departments(id),
        code          TEXT NOT NULL UNIQUE,
        description   TEXT NOT NULL DEFAULT '',
        active        INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE employees (
        uin           TEXT PRIMARY KEY,
        name          TEXT NOT NULL,
        department_id INTEGER NOT NULL REFERENCES departments(id)
    );

    CREATE TABLE log_entries (
        id               INTEGER PRIMARY KEY,
        entry_uuid       TEXT NOT NULL UNIQUE,
        employee_uin     TEXT NOT NULL REFERENCES employees(uin) ON UPDATE CASCADE,
        entry_date       TEXT NOT NULL,
        hours            REAL NOT NULL CHECK (hours > 0 AND hours <= 24),
        activity_code_id INTEGER NOT NULL REFERENCES activity_codes(id),
        description      TEXT NOT NULL DEFAULT '',
        created_at       TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at       TEXT
    );

    CREATE TABLE generated_reports (
        id             INTEGER PRIMARY KEY,
        employee_uin   TEXT NOT NULL REFERENCES employees(uin) ON UPDATE CASCADE,
        period_start   TEXT NOT NULL,
        period_end     TEXT NOT NULL,
        quarter_scheme TEXT NOT NULL,
        generated_at   TEXT NOT NULL DEFAULT (datetime('now')),
        file_path      TEXT NOT NULL,
        data_hash      TEXT NOT NULL
    );

    CREATE INDEX idx_logs_date       ON log_entries(entry_date);
    CREATE INDEX idx_logs_uin        ON log_entries(employee_uin);
    CREATE INDEX idx_logs_code       ON log_entries(activity_code_id);
    CREATE INDEX idx_reports_uin_per ON generated_reports(employee_uin, period_start, period_end);
    """,
]


def migrate(conn: sqlite3.Connection) -> None:
    """Apply all pending migrations. Idempotent — safe to call on every startup."""
    current: int = conn.execute("PRAGMA user_version").fetchone()[0]
    target = len(_MIGRATIONS)

    if current >= target:
        return

    for i, sql in enumerate(_MIGRATIONS[current:], start=current + 1):
        # Execute each statement separately (executescript auto-commits).
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                conn.execute(stmt)
        conn.execute(f"PRAGMA user_version = {i}")
        conn.commit()
