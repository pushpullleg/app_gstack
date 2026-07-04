from __future__ import annotations

import sqlite3

from activity_logger.models.entities import GeneratedReport


class GeneratedReportRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(
        self,
        employee_uin: str,
        period_start: str,
        period_end: str,
        quarter_scheme: str,
        file_path: str,
        data_hash: str,
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO generated_reports
                (employee_uin, period_start, period_end, quarter_scheme, file_path, data_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (employee_uin, period_start, period_end, quarter_scheme, file_path, data_hash),
        )
        return cur.lastrowid  # type: ignore[return-value]

    def get_latest(
        self,
        employee_uin: str,
        period_start: str,
        period_end: str,
    ) -> GeneratedReport | None:
        """Return the most-recently generated report for a given employee + period, or None."""
        r = self._conn.execute(
            """
            SELECT id, employee_uin, period_start, period_end, quarter_scheme,
                   generated_at, file_path, data_hash
            FROM generated_reports
            WHERE employee_uin=? AND period_start=? AND period_end=?
            ORDER BY generated_at DESC, id DESC
            LIMIT 1
            """,
            (employee_uin, period_start, period_end),
        ).fetchone()
        return _row_to_report(r) if r else None

    def list_for_employee(self, employee_uin: str) -> list[GeneratedReport]:
        rows = self._conn.execute(
            """
            SELECT id, employee_uin, period_start, period_end, quarter_scheme,
                   generated_at, file_path, data_hash
            FROM generated_reports WHERE employee_uin=? ORDER BY generated_at DESC
            """,
            (employee_uin,),
        ).fetchall()
        return [_row_to_report(r) for r in rows]


def _row_to_report(r: sqlite3.Row) -> GeneratedReport:
    return GeneratedReport(
        id=r["id"],
        employee_uin=r["employee_uin"],
        period_start=r["period_start"],
        period_end=r["period_end"],
        quarter_scheme=r["quarter_scheme"],
        generated_at=r["generated_at"],
        file_path=r["file_path"],
        data_hash=r["data_hash"],
    )
