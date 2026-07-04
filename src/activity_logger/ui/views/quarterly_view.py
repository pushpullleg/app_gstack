"""Quarterly Report tab — aggregate grid, PDF generation, divergence warning."""

from __future__ import annotations

import dataclasses
import logging
import os
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QRunnable, QThreadPool, Signal, QObject
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from activity_logger.models.entities import ReportData
from activity_logger.repositories.employees import EmployeeRepo
from activity_logger.repositories.generated_reports import GeneratedReportRepo
from activity_logger.services.aggregation_service import AggregationService
from activity_logger.services.periods import quarter_label, quarter_of, quarter_range
from activity_logger.services.report_service import _compute_hash, generate
from activity_logger.ui.models_qt.aggregate_model import AggregateModel

log = logging.getLogger(__name__)


class _PDFSignals(QObject):
    done = Signal(str)   # archive_path
    error = Signal(str)  # error message


class _PDFWorker(QRunnable):
    """Run build_report on a thread pool; fires done/error signals on finish."""

    def __init__(self, data: ReportData, out_path: Path) -> None:
        super().__init__()
        self.signals = _PDFSignals()
        self._data = data
        self._out_path = out_path

    def run(self) -> None:
        from activity_logger.reports.federal_report import build_report
        try:
            build_report(self._data, self._out_path)
            self.signals.done.emit(str(self._out_path))
        except Exception as exc:  # noqa: BLE001
            log.exception("PDF generation failed")
            self.signals.error.emit(str(exc))


class QuarterlyView(QWidget):
    def __init__(self, conn: sqlite3.Connection, cfg: dict, parent=None) -> None:
        super().__init__(parent)
        self._conn = conn
        self._cfg = cfg
        self._model = AggregateModel()
        self._current_data: ReportData | None = None

        self._build_ui()
        self._populate_quarter_combo()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)

        # ── Selection group ───────────────────────────────────────────────────
        sel_group = QGroupBox("Report Parameters")
        sel_form = QFormLayout(sel_group)

        # Employee UIN
        uin_row = QHBoxLayout()
        self._uin_edit = QLineEdit()
        self._uin_edit.setPlaceholderText("Employee UIN (leave blank for All)")
        self._uin_edit.setMaximumWidth(220)
        uin_row.addWidget(self._uin_edit)
        sel_form.addRow("Employee UIN:", uin_row)

        # Year + Quarter
        yq_row = QHBoxLayout()
        self._year_spin = QSpinBox()
        self._year_spin.setRange(2000, 2099)
        self._year_spin.setValue(date.today().year)
        yq_row.addWidget(QLabel("Year:"))
        yq_row.addWidget(self._year_spin)
        yq_row.addSpacing(16)
        yq_row.addWidget(QLabel("Quarter:"))
        self._quarter_combo = QComboBox()
        self._quarter_combo.setMinimumWidth(120)
        yq_row.addWidget(self._quarter_combo)
        yq_row.addStretch()
        sel_form.addRow("Period:", yq_row)

        load_btn = QPushButton("Load Data")
        load_btn.clicked.connect(self._load_data)
        sel_form.addRow("", load_btn)

        root.addWidget(sel_group)

        # ── Aggregate table ───────────────────────────────────────────────────
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setEditTriggers(QTableView.NoEditTriggers)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self._table)

        # ── Grand total label ─────────────────────────────────────────────────
        total_row = QHBoxLayout()
        total_row.addStretch()
        total_row.addWidget(QLabel("Grand Total:"))
        self._total_label = QLabel("—")
        self._total_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        total_row.addWidget(self._total_label)
        root.addLayout(total_row)

        # ── Action buttons ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._gen_btn = QPushButton("Generate PDF…")
        self._gen_btn.setEnabled(False)
        self._gen_btn.clicked.connect(self._generate_pdf)
        btn_row.addStretch()
        btn_row.addWidget(self._gen_btn)
        root.addLayout(btn_row)

        self._status_label = QLabel()
        root.addWidget(self._status_label)

    def _populate_quarter_combo(self) -> None:
        scheme = self._cfg.get("quarter_scheme", "calendar")
        today = date.today()
        cur_year, cur_q = quarter_of(scheme, today)
        self._year_spin.setValue(cur_year)
        self._quarter_combo.clear()
        for q in range(1, 5):
            lbl = quarter_label(scheme, cur_year, q)
            self._quarter_combo.addItem(lbl, userData=q)
        # Select current quarter
        for i in range(self._quarter_combo.count()):
            if self._quarter_combo.itemData(i) == cur_q:
                self._quarter_combo.setCurrentIndex(i)

    # ── slots ─────────────────────────────────────────────────────────────────

    def _load_data(self) -> None:
        scheme = self._cfg.get("quarter_scheme", "calendar")
        year = self._year_spin.value()
        quarter = self._quarter_combo.currentData()
        if quarter is None:
            return

        # Update quarter labels for selected year (they may differ in fiscal mode)
        cur_labels = []
        for q in range(1, 5):
            cur_labels.append(quarter_label(scheme, year, q))
        cur_q_idx = self._quarter_combo.currentIndex()
        self._quarter_combo.blockSignals(True)
        for i, lbl in enumerate(cur_labels):
            self._quarter_combo.setItemText(i, lbl)
        self._quarter_combo.setCurrentIndex(cur_q_idx)
        self._quarter_combo.blockSignals(False)
        quarter = self._quarter_combo.currentData()

        period = quarter_range(scheme, year, quarter)
        uin = self._uin_edit.text().strip()

        svc = AggregationService(self._conn)
        if uin:
            rows = svc.quarterly_totals(uin, period)
        else:
            # All-employee browse mode: flatten into a single list
            all_data = svc.quarterly_totals_all(period)
            from activity_logger.models.entities import ReportCodeRow
            combined: dict[str, ReportCodeRow] = {}
            for _, emp_rows in all_data:
                for r in emp_rows:
                    if r.code in combined:
                        combined[r.code] = ReportCodeRow(r.code, r.description, combined[r.code].hours + r.hours)
                    else:
                        combined[r.code] = r
            rows = sorted(combined.values(), key=lambda r: r.code)

        self._model.load(rows)
        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setStretchLastSection(True)
        grand_total = self._model.grand_total()
        self._total_label.setText(f"{grand_total:.2f} hrs")

        if uin and rows:
            q_lbl = quarter_label(scheme, year, quarter)
            # Build and cache ReportData for PDF generation
            emp_repo = EmployeeRepo(self._conn)
            emp = emp_repo.get_by_uin(uin)
            emp_name = emp.name if emp else uin
            # Get dept code from most common code in rows
            from activity_logger.repositories.departments import DepartmentRepo
            from activity_logger.repositories.activity_codes import ActivityCodeRepo
            dept_code = ""
            if emp:
                dept = DepartmentRepo(self._conn).get_by_id(emp.department_id)
                if dept:
                    dept_code = dept.code

            self._current_data = ReportData(
                employee_uin=uin,
                employee_name=emp_name,
                department_code=dept_code,
                period_start=period.start,
                period_end=period.end,
                quarter_scheme=scheme,
                org_name=self._cfg.get("org_name", "YOUR ORGANIZATION NAME"),
                quarter_label=q_lbl,
                rows=tuple(rows),
                grand_total=grand_total,
                generation_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            self._gen_btn.setEnabled(True)
            self._status_label.setText(
                f"Loaded {len(rows)} code(s) for {uin} — {q_lbl} ({period.start} to {period.end})"
            )
        else:
            self._current_data = None
            self._gen_btn.setEnabled(False)
            if uin:
                self._status_label.setText("No entries for this employee / period.")
            else:
                self._status_label.setText(f"Showing all employees (PDF requires a specific UIN).")

    def _generate_pdf(self) -> None:
        if self._current_data is None:
            return

        # Check for prior divergence before showing save dialog
        scheme = self._cfg.get("quarter_scheme", "calendar")
        period_start = self._current_data.period_start.isoformat()
        period_end = self._current_data.period_end.isoformat()
        repo = GeneratedReportRepo(self._conn)
        new_hash = _compute_hash(self._current_data)
        prior = repo.get_latest(self._current_data.employee_uin, period_start, period_end)
        if prior and prior.data_hash != new_hash:
            reply = QMessageBox.warning(
                self,
                "Data Changed",
                f"The data for this period has changed since the report generated on "
                f"{prior.generated_at[:10]}. The previously signed copy may no longer match.\n\n"
                "Generate a new report anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        # Save dialog
        default_name = (
            f"{self._current_data.employee_uin}_{self._current_data.quarter_label.replace(' ', '_')}.pdf"
        )
        out_path_str, _ = QFileDialog.getSaveFileName(
            self, "Save Report", default_name, "PDF Files (*.pdf)"
        )
        if not out_path_str:
            return

        out_path = Path(out_path_str)
        self._gen_btn.setEnabled(False)
        self._status_label.setText("Generating PDF…")

        # Refresh generation_timestamp for the actual PDF
        data = dataclasses.replace(
            self._current_data,
            generation_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        worker = _PDFWorker(data, out_path)
        worker.signals.done.connect(lambda p: self._on_pdf_done(p, data))
        worker.signals.error.connect(self._on_pdf_error)
        QThreadPool.globalInstance().start(worker)

    def _on_pdf_done(self, out_path_str: str, data: ReportData) -> None:
        out_path = Path(out_path_str)
        # Archive (main thread — connection safe)
        try:
            from activity_logger import config
            import shutil
            from activity_logger.services.report_service import _archive_filename, _compute_hash
            archive_dir = config.REPORTS_DIR
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / _archive_filename(data)
            shutil.copy2(str(out_path), str(archive_path))
            GeneratedReportRepo(self._conn).insert(
                employee_uin=data.employee_uin,
                period_start=data.period_start.isoformat(),
                period_end=data.period_end.isoformat(),
                quarter_scheme=data.quarter_scheme,
                file_path=str(archive_path),
                data_hash=_compute_hash(data),
            )
            self._conn.commit()
        except Exception as exc:  # noqa: BLE001
            log.warning("Archive step failed: %s", exc)

        self._gen_btn.setEnabled(True)
        self._status_label.setText(f"Report saved: {out_path_str}")

        # Open in default viewer
        try:
            if sys.platform == "win32":
                os.startfile(str(out_path))
            elif sys.platform == "darwin":
                os.system(f'open "{out_path}"')
            else:
                os.system(f'xdg-open "{out_path}"')
        except Exception:  # noqa: BLE001
            pass

    def _on_pdf_error(self, msg: str) -> None:
        self._gen_btn.setEnabled(True)
        self._status_label.setText("PDF generation failed.")
        QMessageBox.critical(self, "PDF Error", f"Failed to generate PDF:\n\n{msg}")
