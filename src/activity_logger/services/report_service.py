"""Generate a report, archive the PDF copy, detect divergence from prior signed copies.

data_hash is SHA-256 over ReportData EXCLUDING generation_timestamp — so regenerating
unchanged data produces the same hash and no divergence warning.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from activity_logger import config
from activity_logger.models.entities import ReportData
from activity_logger.repositories.generated_reports import GeneratedReportRepo
from activity_logger.reports.federal_report import build_report


def _compute_hash(data: ReportData) -> str:
    """SHA-256 over a stable serialisation of ReportData excluding generation_timestamp."""
    payload = {
        "employee_uin": data.employee_uin,
        "employee_name": data.employee_name,
        "department_code": data.department_code,
        "period_start": data.period_start.isoformat(),
        "period_end": data.period_end.isoformat(),
        "quarter_scheme": data.quarter_scheme,
        "org_name": data.org_name,
        "quarter_label": data.quarter_label,
        "rows": [(r.code, r.description, r.hours) for r in data.rows],
        "grand_total": data.grand_total,
    }
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _archive_filename(data: ReportData) -> str:
    """Windows-safe archive filename: {UIN}_{YYYY}Q{n}_{YYYYMMDD-HHMMSS}.pdf"""
    from activity_logger.services.periods import quarter_of
    year, quarter = quarter_of(data.quarter_scheme, data.period_start)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_uin = data.employee_uin.replace("/", "-").replace("\\", "-")
    return f"{safe_uin}_{year}Q{quarter}_{ts}.pdf"


def generate(
    conn: sqlite3.Connection,
    data: ReportData,
    out_path: Path,
) -> tuple[Path, str | None]:
    """Generate the report PDF, archive it, and return (archive_path, warning_message|None).

    warning_message is non-None only when data changed since the last archived report
    for this employee+period (i.e., hashes differ).
    """
    repo = GeneratedReportRepo(conn)
    data_hash = _compute_hash(data)
    period_start_str = data.period_start.isoformat()
    period_end_str = data.period_end.isoformat()

    warning: str | None = None
    prior = repo.get_latest(data.employee_uin, period_start_str, period_end_str)
    if prior is not None and prior.data_hash != data_hash:
        warning = (
            f"Data has changed since the report generated on {prior.generated_at[:10]} — "
            "the signed copy may no longer match."
        )

    # Build the PDF to the requested path.
    build_report(data, out_path)

    # Archive a copy under the data dir.
    archive_dir = config.REPORTS_DIR
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_name = _archive_filename(data)
    archive_path = archive_dir / archive_name
    shutil.copy2(str(out_path), str(archive_path))

    repo.insert(
        employee_uin=data.employee_uin,
        period_start=period_start_str,
        period_end=period_end_str,
        quarter_scheme=data.quarter_scheme,
        file_path=str(archive_path),
        data_hash=data_hash,
    )
    conn.commit()

    return archive_path, warning
