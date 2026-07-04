"""Input validation rules — UIN pattern, hours bounds, dept/code consistency."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ValidationError:
    field: str
    message: str


def validate_uin(uin: str, pattern: str) -> list[ValidationError]:
    if not uin.strip():
        return [ValidationError("uin", "UIN is required.")]
    if not re.fullmatch(pattern, uin):
        return [ValidationError("uin", f"UIN does not match expected format ({pattern}).")]
    return []


def validate_hours(hours: float) -> list[ValidationError]:
    if hours <= 0:
        return [ValidationError("hours", "Hours must be greater than 0.")]
    if hours > 24:
        return [ValidationError("hours", "Hours cannot exceed 24 per entry.")]
    return []


def validate_entry_date(entry_date: date) -> list[ValidationError]:
    today = date.today()
    if entry_date > today:
        return [ValidationError("entry_date", "Entry date cannot be in the future.")]
    return []


def validate_entry(
    *,
    uin: str,
    name: str,
    hours: float,
    entry_date: date,
    activity_code_id: int | None,
    activity_code_department_id: int | None,
    selected_department_id: int | None,
    uin_pattern: str,
) -> list[ValidationError]:
    """Full entry validation. Returns a (possibly empty) list of errors."""
    errors: list[ValidationError] = []

    if not name.strip():
        errors.append(ValidationError("name", "Name is required."))

    errors.extend(validate_uin(uin, uin_pattern))
    errors.extend(validate_hours(hours))
    errors.extend(validate_entry_date(entry_date))

    if activity_code_id is None:
        errors.append(ValidationError("activity_code", "Activity code is required."))
    elif (
        activity_code_department_id is not None
        and selected_department_id is not None
        and activity_code_department_id != selected_department_id
    ):
        errors.append(ValidationError("activity_code", "Activity code does not belong to the selected department."))

    return errors
