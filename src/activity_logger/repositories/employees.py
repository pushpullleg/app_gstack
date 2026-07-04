from __future__ import annotations

import sqlite3

from activity_logger.models.entities import Employee


class EmployeeRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(self, uin: str, name: str, department_id: int) -> None:
        """Insert employee or update name/dept if UIN already exists."""
        self._conn.execute(
            """
            INSERT INTO employees(uin, name, department_id) VALUES(?, ?, ?)
            ON CONFLICT(uin) DO UPDATE SET name=excluded.name,
                                           department_id=excluded.department_id
            """,
            (uin, name, department_id),
        )

    def get_by_uin(self, uin: str) -> Employee | None:
        r = self._conn.execute(
            "SELECT uin, name, department_id FROM employees WHERE uin=?", (uin,)
        ).fetchone()
        if r is None:
            return None
        return Employee(uin=r["uin"], name=r["name"], department_id=r["department_id"])

    def list_all(self) -> list[Employee]:
        rows = self._conn.execute(
            "SELECT uin, name, department_id FROM employees ORDER BY name"
        ).fetchall()
        return [Employee(uin=r["uin"], name=r["name"], department_id=r["department_id"]) for r in rows]

    def search(self, term: str) -> list[Employee]:
        """Prefix search on UIN or name for QCompleter feed."""
        pattern = f"{term}%"
        rows = self._conn.execute(
            "SELECT uin, name, department_id FROM employees WHERE uin LIKE ? OR name LIKE ? ORDER BY name LIMIT 50",
            (pattern, pattern),
        ).fetchall()
        return [Employee(uin=r["uin"], name=r["name"], department_id=r["department_id"]) for r in rows]
