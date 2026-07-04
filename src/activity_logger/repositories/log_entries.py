from __future__ import annotations

import sqlite3
from datetime import date

from activity_logger.models.entities import LogEntry


class LogEntryRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(
        self,
        entry_uuid: str,
        employee_uin: str,
        entry_date: date,
        hours: float,
        activity_code_id: int,
        description: str,
        created_at: str | None = None,
    ) -> int:
        """Insert a log entry. Returns the new row id."""
        kwargs: dict = {
            "entry_uuid": entry_uuid,
            "employee_uin": employee_uin,
            "entry_date": entry_date.isoformat(),
            "hours": hours,
            "activity_code_id": activity_code_id,
            "description": description,
        }
        if created_at is not None:
            cur = self._conn.execute(
                """
                INSERT INTO log_entries
                    (entry_uuid, employee_uin, entry_date, hours, activity_code_id,
                     description, created_at)
                VALUES (:entry_uuid, :employee_uin, :entry_date, :hours,
                        :activity_code_id, :description, :created_at)
                """,
                {**kwargs, "created_at": created_at},
            )
        else:
            cur = self._conn.execute(
                """
                INSERT INTO log_entries
                    (entry_uuid, employee_uin, entry_date, hours, activity_code_id, description)
                VALUES (:entry_uuid, :employee_uin, :entry_date, :hours,
                        :activity_code_id, :description)
                """,
                kwargs,
            )
        return cur.lastrowid  # type: ignore[return-value]

    def get_by_uuid(self, entry_uuid: str) -> LogEntry | None:
        r = self._conn.execute(
            "SELECT id,entry_uuid,employee_uin,entry_date,hours,activity_code_id,"
            "description,created_at,updated_at FROM log_entries WHERE entry_uuid=?",
            (entry_uuid,),
        ).fetchone()
        return _row_to_entry(r) if r else None

    def update(
        self,
        entry_id: int,
        hours: float,
        activity_code_id: int,
        description: str,
    ) -> None:
        self._conn.execute(
            """
            UPDATE log_entries
            SET hours=?, activity_code_id=?, description=?, updated_at=datetime('now')
            WHERE id=?
            """,
            (hours, activity_code_id, description, entry_id),
        )

    def delete(self, entry_id: int) -> None:
        self._conn.execute("DELETE FROM log_entries WHERE id=?", (entry_id,))

    def get_by_date(self, entry_date: date) -> list[LogEntry]:
        rows = self._conn.execute(
            "SELECT id,entry_uuid,employee_uin,entry_date,hours,activity_code_id,"
            "description,created_at,updated_at FROM log_entries WHERE entry_date=? ORDER BY created_at",
            (entry_date.isoformat(),),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def get_by_period(self, uin: str, start: date, end: date) -> list[LogEntry]:
        rows = self._conn.execute(
            "SELECT id,entry_uuid,employee_uin,entry_date,hours,activity_code_id,"
            "description,created_at,updated_at FROM log_entries "
            "WHERE employee_uin=? AND entry_date>=? AND entry_date<=? ORDER BY entry_date",
            (uin, start.isoformat(), end.isoformat()),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def get_by_month(self, year: int, month: int) -> list[LogEntry]:
        prefix = f"{year:04d}-{month:02d}-%"
        rows = self._conn.execute(
            "SELECT id,entry_uuid,employee_uin,entry_date,hours,activity_code_id,"
            "description,created_at,updated_at FROM log_entries "
            "WHERE entry_date LIKE ? ORDER BY entry_date DESC, created_at DESC",
            (prefix,),
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def get_by_id(self, entry_id: int) -> LogEntry | None:
        r = self._conn.execute(
            "SELECT id,entry_uuid,employee_uin,entry_date,hours,activity_code_id,"
            "description,created_at,updated_at FROM log_entries WHERE id=?",
            (entry_id,),
        ).fetchone()
        return _row_to_entry(r) if r else None

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM log_entries").fetchone()[0]


def _row_to_entry(r: sqlite3.Row) -> LogEntry:
    return LogEntry(
        id=r["id"],
        entry_uuid=r["entry_uuid"],
        employee_uin=r["employee_uin"],
        entry_date=date.fromisoformat(r["entry_date"]),
        hours=r["hours"],
        activity_code_id=r["activity_code_id"],
        description=r["description"],
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )
