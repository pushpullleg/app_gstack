"""Frozen dataclasses — the shared data contract between layers.

No Qt, no ReportLab, no sqlite3 here. These travel freely across threads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Department:
    id: int
    code: str
    name: str
    active: bool = True


@dataclass(frozen=True)
class ActivityCode:
    id: int
    department_id: int
    code: str
    description: str
    active: bool = True


@dataclass(frozen=True)
class Employee:
    uin: str          # exact case as entered; see ARCHITECTURE.md §12
    name: str
    department_id: int


@dataclass(frozen=True)
class LogEntry:
    id: int
    entry_uuid: str   # uuid4 assigned at insert; CSV merge key
    employee_uin: str
    entry_date: date
    hours: float
    activity_code_id: int
    description: str
    created_at: str   # ISO-8601 datetime string
    updated_at: str | None = None


@dataclass(frozen=True)
class ReportCodeRow:
    code: str
    description: str
    hours: float


@dataclass(frozen=True)
class ReportData:
    """All data needed to render a federal quarterly report PDF.

    Passed to federal_report.build_report() — no DB access inside that function.
    generation_timestamp is excluded from data_hash (see ARCHITECTURE.md §6).
    """
    employee_uin: str
    employee_name: str
    department_code: str
    period_start: date
    period_end: date
    quarter_scheme: str         # 'calendar' | 'federal_fiscal'
    org_name: str
    quarter_label: str          # e.g. 'Q3 2026' or 'FY26 Q3'
    rows: tuple[ReportCodeRow, ...]
    grand_total: float
    generation_timestamp: str   # excluded from data_hash; injected by report_service


@dataclass(frozen=True)
class GeneratedReport:
    id: int
    employee_uin: str
    period_start: str
    period_end: str
    quarter_scheme: str
    generated_at: str
    file_path: str
    data_hash: str
