from __future__ import annotations

import sqlite3

from activity_logger.models.entities import Department


class DepartmentRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_active(self) -> list[Department]:
        rows = self._conn.execute(
            "SELECT id, code, name, active FROM departments WHERE active=1 ORDER BY code"
        ).fetchall()
        return [Department(id=r["id"], code=r["code"], name=r["name"], active=bool(r["active"])) for r in rows]

    def get_by_code(self, code: str) -> Department | None:
        r = self._conn.execute(
            "SELECT id, code, name, active FROM departments WHERE code=?", (code,)
        ).fetchone()
        if r is None:
            return None
        return Department(id=r["id"], code=r["code"], name=r["name"], active=bool(r["active"]))

    def get_by_id(self, dept_id: int) -> Department | None:
        r = self._conn.execute(
            "SELECT id, code, name, active FROM departments WHERE id=?", (dept_id,)
        ).fetchone()
        if r is None:
            return None
        return Department(id=r["id"], code=r["code"], name=r["name"], active=bool(r["active"]))
