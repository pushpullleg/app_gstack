"""Seed the department and activity-code catalog.

Replace the placeholder descriptions with real codes before rollout.
Adding a new department is an INSERT here; no schema or logic change needed.
"""

from __future__ import annotations

import sqlite3

_DEPARTMENTS = [
    ("CP", "Community Programs"),
    ("MMC", "Maintenance, Materials & Custodial"),
    ("ADV", "Administrative Services"),
]

# (department_code, activity_code, description)
# Replace descriptions with real catalog text before rollout.
_ACTIVITY_CODES: list[tuple[str, str, str]] = [
    ("CP", "CP-01", "Community Program Activity 1 (placeholder)"),
    ("CP", "CP-02", "Community Program Activity 2 (placeholder)"),
    ("CP", "CP-03", "Community Program Activity 3 (placeholder)"),
    ("MMC", "MMC-01", "Maintenance Activity 1 (placeholder)"),
    ("MMC", "MMC-02", "Maintenance Activity 2 (placeholder)"),
    ("MMC", "MMC-03", "Maintenance Activity 3 (placeholder)"),
    ("ADV", "ADV-01", "Administrative Activity 1 (placeholder)"),
    ("ADV", "ADV-02", "Administrative Activity 2 (placeholder)"),
    ("ADV", "ADV-03", "Administrative Activity 3 (placeholder)"),
]


def seed(conn: sqlite3.Connection) -> None:
    """Insert seed rows; skip if they already exist (idempotent)."""
    for code, name in _DEPARTMENTS:
        conn.execute(
            "INSERT OR IGNORE INTO departments(code, name) VALUES (?, ?)",
            (code, name),
        )

    for dept_code, act_code, description in _ACTIVITY_CODES:
        conn.execute(
            """
            INSERT OR IGNORE INTO activity_codes(department_id, code, description)
            SELECT d.id, ?, ?
            FROM departments d WHERE d.code = ?
            """,
            (act_code, description, dept_code),
        )

    conn.commit()
