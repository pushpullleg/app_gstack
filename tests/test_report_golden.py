"""Golden PDF: text extraction, XML-special chars, signature labels, grand total."""

from __future__ import annotations

from datetime import date

import pypdf
import pytest

from activity_logger.models.entities import ReportCodeRow, ReportData
from activity_logger.reports.federal_report import build_report


def _data(**overrides) -> ReportData:
    defaults: dict = dict(
        employee_uin="G-099",
        employee_name="Bob Torres",
        department_code="MMC",
        period_start=date(2026, 7, 1),
        period_end=date(2026, 9, 30),
        quarter_scheme="calendar",
        org_name="Springfield City Services",
        quarter_label="Q3 2026",
        rows=(
            ReportCodeRow("MMC-01", "General Maintenance", 32.0),
            ReportCodeRow("MMC-02", "Custodial Services", 16.0),
        ),
        grand_total=48.0,
        generation_timestamp="2026-10-01 09:00:00",
    )
    defaults.update(overrides)
    return ReportData(**defaults)


def _text(pdf_path) -> str:
    reader = pypdf.PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_pdf_is_valid(tmp_path) -> None:
    out = tmp_path / "golden.pdf"
    build_report(_data(), out)
    reader = pypdf.PdfReader(str(out))
    assert len(reader.pages) >= 1


def test_pdf_contains_org_name(tmp_path) -> None:
    out = tmp_path / "golden.pdf"
    build_report(_data(), out)
    assert "Springfield City Services" in _text(out)


def test_pdf_contains_quarter_label(tmp_path) -> None:
    out = tmp_path / "golden.pdf"
    build_report(_data(), out)
    assert "Q3 2026" in _text(out)


def test_pdf_contains_employee_uin(tmp_path) -> None:
    out = tmp_path / "golden.pdf"
    build_report(_data(), out)
    assert "G-099" in _text(out)


def test_pdf_contains_employee_name(tmp_path) -> None:
    out = tmp_path / "golden.pdf"
    build_report(_data(), out)
    assert "Bob Torres" in _text(out)


def test_pdf_xml_special_chars_do_not_crash(tmp_path) -> None:
    """Mandatory: description with < and & must not crash ReportLab."""
    data = _data(
        rows=(ReportCodeRow("MMC-01", "Hours 3 < 4 & done", 8.0),),
        grand_total=8.0,
    )
    out = tmp_path / "special.pdf"
    build_report(data, out)   # must not raise
    assert out.exists() and out.stat().st_size > 0
    text = _text(out)
    assert "MMC-01" in text


def test_pdf_grand_total_displayed(tmp_path) -> None:
    rows = (
        ReportCodeRow("MMC-01", "Maintenance", 30.0),
        ReportCodeRow("MMC-02", "Custodial", 18.5),
    )
    data = _data(rows=rows, grand_total=sum(r.hours for r in rows))
    out = tmp_path / "totals.pdf"
    build_report(data, out)
    assert "48.50" in _text(out)


def test_pdf_signature_labels_present(tmp_path) -> None:
    out = tmp_path / "sigs.pdf"
    build_report(_data(), out)
    text = _text(out)
    assert "Employee" in text
    assert "Supervisor" in text
    assert "Director" in text


def test_pdf_activity_codes_present(tmp_path) -> None:
    out = tmp_path / "codes.pdf"
    build_report(_data(), out)
    text = _text(out)
    assert "MMC-01" in text
    assert "MMC-02" in text
