"""Monthly and quarterly aggregation queries."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from activity_logger.models.entities import ReportCodeRow, ReportData
from activity_logger.services.periods import DateRange


@dataclass(frozen=True)
class MonthlyRow:
    entry_id: int
    entry_uuid: str
    employee_uin: str
    employee_name: str
    department_code: str
    activity_code: str
    entry_date: date
    hours: float
    description: str


class AggregationService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def monthly_rows(self, year: int, month: int) -> list[MonthlyRow]:
        """All log entries for a calendar month, joined with employee + code + dept."""
        prefix = f"{year:04d}-{month:02d}-%"
        rows = self._conn.execute(
            """
            SELECT l.id, l.entry_uuid, l.employee_uin, e.name AS employee_name,
                   d.code AS department_code, ac.code AS activity_code,
                   l.entry_date, l.hours, l.description
            FROM log_entries l
            JOIN employees e ON e.uin = l.employee_uin
            JOIN activity_codes ac ON ac.id = l.activity_code_id
            JOIN departments d ON d.id = ac.department_id
            WHERE l.entry_date LIKE ?
            ORDER BY l.entry_date DESC, e.name, ac.code
            """,
            (prefix,),
        ).fetchall()
        return [
            MonthlyRow(
                entry_id=r["id"],
                entry_uuid=r["entry_uuid"],
                employee_uin=r["employee_uin"],
                employee_name=r["employee_name"],
                department_code=r["department_code"],
                activity_code=r["activity_code"],
                entry_date=date.fromisoformat(r["entry_date"]),
                hours=r["hours"],
                description=r["description"],
            )
            for r in rows
        ]

    def quarterly_totals(
        self, uin: str, period: DateRange
    ) -> list[ReportCodeRow]:
        """Per-code hour totals for an employee over a date range."""
        rows = self._conn.execute(
            """
            SELECT ac.code, ac.description, SUM(l.hours) AS total_hours
            FROM log_entries l
            JOIN activity_codes ac ON ac.id = l.activity_code_id
            WHERE l.employee_uin = ?
              AND l.entry_date >= ?
              AND l.entry_date <= ?
            GROUP BY ac.id
            ORDER BY ac.code
            """,
            (uin, period.start.isoformat(), period.end.isoformat()),
        ).fetchall()
        return [
            ReportCodeRow(
                code=r["code"],
                description=r["description"],
                hours=round(r["total_hours"], 2),
            )
            for r in rows
        ]

    def quarterly_totals_all(self, period: DateRange) -> list[tuple[str, list[ReportCodeRow]]]:
        """Per-employee, per-code totals for the browse view (all employees)."""
        uins = self._conn.execute(
            """
            SELECT DISTINCT l.employee_uin
            FROM log_entries l
            WHERE l.entry_date >= ? AND l.entry_date <= ?
            ORDER BY l.employee_uin
            """,
            (period.start.isoformat(), period.end.isoformat()),
        ).fetchall()
        return [(r["employee_uin"], self.quarterly_totals(r["employee_uin"], period)) for r in uins]
