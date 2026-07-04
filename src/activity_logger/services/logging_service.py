"""Save, update, and delete log entries — the write path for the Data Entry view."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date

from activity_logger import config
from activity_logger.repositories.activity_codes import ActivityCodeRepo
from activity_logger.repositories.departments import DepartmentRepo
from activity_logger.repositories.employees import EmployeeRepo
from activity_logger.repositories.log_entries import LogEntryRepo
from activity_logger.services.validation import ValidationError, validate_entry


class LoggingService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._log_repo = LogEntryRepo(conn)
        self._emp_repo = EmployeeRepo(conn)
        self._code_repo = ActivityCodeRepo(conn)
        self._dept_repo = DepartmentRepo(conn)

    def save_entry(
        self,
        *,
        name: str,
        uin: str,
        department_id: int,
        activity_code_id: int,
        entry_date: date,
        hours: float,
        description: str,
    ) -> tuple[int, list[ValidationError]]:
        """Validate and save. Returns (entry_id, errors). entry_id=0 on failure."""
        code = self._code_repo.get_by_id(activity_code_id)
        cfg = config.get()
        errors = validate_entry(
            uin=uin,
            name=name,
            hours=hours,
            entry_date=entry_date,
            activity_code_id=activity_code_id,
            activity_code_department_id=code.department_id if code else None,
            selected_department_id=department_id,
            uin_pattern=cfg["uin_pattern"],
        )
        if errors:
            return 0, errors

        self._emp_repo.upsert(uin, name, department_id)
        entry_uuid = str(uuid.uuid4())
        entry_id = self._log_repo.insert(
            entry_uuid=entry_uuid,
            employee_uin=uin,
            entry_date=entry_date,
            hours=hours,
            activity_code_id=activity_code_id,
            description=description,
        )
        self._conn.commit()
        return entry_id, []

    def update_entry(
        self,
        entry_id: int,
        *,
        hours: float,
        activity_code_id: int,
        description: str,
    ) -> list[ValidationError]:
        from activity_logger.services.validation import validate_hours
        errors = validate_hours(hours)
        if errors:
            return errors
        self._log_repo.update(entry_id, hours, activity_code_id, description)
        self._conn.commit()
        return []

    def delete_entry(self, entry_id: int) -> None:
        self._log_repo.delete(entry_id)
        self._conn.commit()
