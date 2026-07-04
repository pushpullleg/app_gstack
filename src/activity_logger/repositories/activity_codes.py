from __future__ import annotations

import sqlite3

from activity_logger.models.entities import ActivityCode


class ActivityCodeRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_by_department(self, department_id: int) -> list[ActivityCode]:
        rows = self._conn.execute(
            """
            SELECT id, department_id, code, description, active
            FROM activity_codes
            WHERE department_id=? AND active=1
            ORDER BY code
            """,
            (department_id,),
        ).fetchall()
        return [
            ActivityCode(
                id=r["id"],
                department_id=r["department_id"],
                code=r["code"],
                description=r["description"],
                active=bool(r["active"]),
            )
            for r in rows
        ]

    def get_by_id(self, code_id: int) -> ActivityCode | None:
        r = self._conn.execute(
            "SELECT id, department_id, code, description, active FROM activity_codes WHERE id=?",
            (code_id,),
        ).fetchone()
        if r is None:
            return None
        return ActivityCode(
            id=r["id"],
            department_id=r["department_id"],
            code=r["code"],
            description=r["description"],
            active=bool(r["active"]),
        )

    def get_by_code(self, code: str) -> ActivityCode | None:
        r = self._conn.execute(
            "SELECT id, department_id, code, description, active FROM activity_codes WHERE code=?",
            (code,),
        ).fetchone()
        if r is None:
            return None
        return ActivityCode(
            id=r["id"],
            department_id=r["department_id"],
            code=r["code"],
            description=r["description"],
            active=bool(r["active"]),
        )

    def list_all_active(self) -> list[ActivityCode]:
        rows = self._conn.execute(
            "SELECT id, department_id, code, description, active FROM activity_codes WHERE active=1 ORDER BY code"
        ).fetchall()
        return [
            ActivityCode(
                id=r["id"],
                department_id=r["department_id"],
                code=r["code"],
                description=r["description"],
                active=bool(r["active"]),
            )
            for r in rows
        ]
