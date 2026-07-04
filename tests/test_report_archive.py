"""Report archive: hash stability, divergence warning, filename format."""

from __future__ import annotations

import re
from datetime import date

import pytest

from activity_logger.models.entities import ReportCodeRow, ReportData
from activity_logger.services.report_service import _compute_hash, generate


def _data(**overrides) -> ReportData:
    defaults: dict = dict(
        employee_uin="U-001",
        employee_name="Alice Smith",
        department_code="CP",
        period_start=date(2026, 7, 1),
        period_end=date(2026, 9, 30),
        quarter_scheme="calendar",
        org_name="City of Springfield",
        quarter_label="Q3 2026",
        rows=(ReportCodeRow("CP-01", "Community Outreach", 40.0),),
        grand_total=40.0,
        generation_timestamp="2026-10-01 09:00:00",
    )
    defaults.update(overrides)
    return ReportData(**defaults)


@pytest.fixture()
def archive_dir(monkeypatch, tmp_path):
    reports = tmp_path / "reports"
    monkeypatch.setattr("activity_logger.config.REPORTS_DIR", reports)
    return reports


@pytest.fixture()
def db_with_employee(db):
    """db fixture with U-001 / Alice Smith in CP department."""
    dept_id = db.execute("SELECT id FROM departments WHERE code='CP'").fetchone()[0]
    db.execute(
        "INSERT OR IGNORE INTO employees(uin,name,department_id) VALUES('U-001','Alice Smith',?)",
        (dept_id,),
    )
    db.commit()
    return db


def test_no_prior_no_warning(db_with_employee, archive_dir, tmp_path) -> None:
    """First generation for a period must never produce a warning."""
    out = tmp_path / "r.pdf"
    _, warning = generate(db_with_employee, _data(), out)
    assert warning is None


def test_same_data_no_warning(db_with_employee, archive_dir, tmp_path) -> None:
    d = _data()
    generate(db_with_employee, d, tmp_path / "r1.pdf")
    _, warning = generate(db_with_employee, d, tmp_path / "r2.pdf")
    assert warning is None


def test_changed_data_warning(db_with_employee, archive_dir, tmp_path) -> None:
    generate(db_with_employee, _data(), tmp_path / "r1.pdf")
    d2 = _data(rows=(ReportCodeRow("CP-01", "Community Outreach", 50.0),), grand_total=50.0)
    _, warning = generate(db_with_employee, d2, tmp_path / "r2.pdf")
    assert warning is not None
    assert "changed" in warning.lower()


def test_timestamp_excluded_from_hash(db_with_employee, archive_dir, tmp_path) -> None:
    """Regenerating identical data with a different timestamp must not warn."""
    generate(db_with_employee, _data(generation_timestamp="2026-10-01 09:00:00"), tmp_path / "r1.pdf")
    _, warning = generate(db_with_employee, _data(generation_timestamp="2026-10-02 12:00:00"), tmp_path / "r2.pdf")
    assert warning is None


def test_archive_file_exists(db_with_employee, archive_dir, tmp_path) -> None:
    archive_path, _ = generate(db_with_employee, _data(), tmp_path / "r.pdf")
    assert archive_path.exists()
    assert archive_path.stat().st_size > 0


def test_filename_windows_safe(db_with_employee, archive_dir, tmp_path) -> None:
    """Archive filename: no forbidden chars, matches {UIN}_{YYYY}Q{n}_{YYYYMMDD-HHMMSS}.pdf."""
    archive_path, _ = generate(db_with_employee, _data(), tmp_path / "r.pdf")
    name = archive_path.name
    # No Windows-forbidden characters (outside the .pdf extension dot)
    stem = name[: name.rfind(".pdf")]
    assert not re.search(r'[\\/:*?"<>|]', stem), f"Forbidden chars in: {name!r}"
    # Structural pattern
    assert re.fullmatch(r"[A-Za-z0-9._-]+_\d{4}Q\d_\d{8}-\d{6}\.pdf", name), (
        f"Filename does not match expected pattern: {name!r}"
    )


def test_hash_deterministic() -> None:
    d = _data()
    assert _compute_hash(d) == _compute_hash(d)


def test_hash_differs_on_data_change() -> None:
    d1 = _data()
    d2 = _data(grand_total=99.0)
    assert _compute_hash(d1) != _compute_hash(d2)
