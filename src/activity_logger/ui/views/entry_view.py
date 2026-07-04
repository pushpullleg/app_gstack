"""Data Entry tab — log a single activity entry for an employee."""

from __future__ import annotations

import sqlite3
from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCompleter,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from activity_logger.repositories.employees import EmployeeRepo
from activity_logger.services.aggregation_service import AggregationService
from activity_logger.services.logging_service import LoggingService
from activity_logger.ui.models_qt.log_table_model import LogTableModel
from activity_logger.ui.widgets.dept_code_picker import DeptCodePicker


class EntryView(QWidget):
    def __init__(self, conn: sqlite3.Connection, cfg: dict, parent=None) -> None:
        super().__init__(parent)
        self._conn = conn
        self._cfg = cfg
        self._logging_svc = LoggingService(conn)
        self._emp_repo = EmployeeRepo(conn)
        self._today_model = LogTableModel()

        self._build_ui()
        self._refresh_completers()
        self._refresh_today()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)

        # ── Employee group ────────────────────────────────────────────────────
        emp_group = QGroupBox("Employee")
        emp_form = QFormLayout(emp_group)
        emp_form.setRowWrapPolicy(QFormLayout.DontWrapRows)

        self._uin_edit = QLineEdit()
        self._uin_edit.setPlaceholderText("e.g. EMP-001")
        self._uin_edit.setToolTip(
            "UIN is case-sensitive: 'a-001' and 'A-001' are different employees."
        )
        self._uin_completer = QCompleter([])
        self._uin_completer.setCaseSensitivity(Qt.CaseSensitive)
        self._uin_edit.setCompleter(self._uin_completer)
        emp_form.addRow("UIN:", self._uin_edit)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Full name")
        self._name_completer = QCompleter([])
        self._name_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._name_edit.setCompleter(self._name_completer)
        emp_form.addRow("Name:", self._name_edit)

        self._uin_error = QLabel()
        self._uin_error.setStyleSheet("color: red;")
        self._uin_error.setVisible(False)
        emp_form.addRow("", self._uin_error)

        self._name_error = QLabel()
        self._name_error.setStyleSheet("color: red;")
        self._name_error.setVisible(False)
        emp_form.addRow("", self._name_error)

        root.addWidget(emp_group)

        # ── Entry group ───────────────────────────────────────────────────────
        entry_group = QGroupBox("Entry")
        entry_form = QFormLayout(entry_group)

        self._date_edit = QDateEdit(QDate.currentDate())
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("yyyy-MM-dd")
        entry_form.addRow("Date:", self._date_edit)

        self._date_error = QLabel()
        self._date_error.setStyleSheet("color: red;")
        self._date_error.setVisible(False)
        entry_form.addRow("", self._date_error)

        self._picker = DeptCodePicker(self._conn)
        entry_form.addRow("Dept / Code:", self._picker)

        self._code_error = QLabel()
        self._code_error.setStyleSheet("color: red;")
        self._code_error.setVisible(False)
        entry_form.addRow("", self._code_error)

        self._hours_spin = QDoubleSpinBox()
        self._hours_spin.setRange(0.25, 24.0)
        self._hours_spin.setSingleStep(0.25)
        self._hours_spin.setDecimals(2)
        self._hours_spin.setValue(1.0)
        self._hours_spin.setSuffix(" hrs")
        entry_form.addRow("Hours:", self._hours_spin)

        self._hours_error = QLabel()
        self._hours_error.setStyleSheet("color: red;")
        self._hours_error.setVisible(False)
        entry_form.addRow("", self._hours_error)

        self._desc_edit = QPlainTextEdit()
        self._desc_edit.setPlaceholderText("Optional description (max 500 chars)")
        self._desc_edit.setMaximumHeight(72)
        entry_form.addRow("Description:", self._desc_edit)

        root.addWidget(entry_group)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._save_btn = QPushButton("Save Entry")
        self._save_btn.setDefault(True)
        self._save_btn.clicked.connect(self._save)
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self._clear)
        btn_row.addStretch()
        btn_row.addWidget(self._save_btn)
        btn_row.addWidget(self._clear_btn)
        root.addLayout(btn_row)

        self._status_label = QLabel()
        root.addWidget(self._status_label)

        # ── Today's entries strip ─────────────────────────────────────────────
        today_label = QLabel(f"Today's entries ({date.today()})")
        today_label.setStyleSheet("font-weight: bold;")
        root.addWidget(today_label)

        self._today_table = QTableView()
        self._today_table.setModel(self._today_model)
        self._today_table.setSelectionBehavior(QTableView.SelectRows)
        self._today_table.setEditTriggers(QTableView.NoEditTriggers)
        self._today_table.horizontalHeader().setStretchLastSection(True)
        self._today_table.setMaximumHeight(160)
        root.addWidget(self._today_table)

        # Connect UIN field for auto-fill
        self._uin_edit.editingFinished.connect(self._on_uin_changed)

    # ── slots ─────────────────────────────────────────────────────────────────

    def _on_uin_changed(self) -> None:
        uin = self._uin_edit.text().strip()
        if not uin:
            return
        emp = self._emp_repo.get_by_uin(uin)
        if emp:
            self._name_edit.setText(emp.name)
            self._picker.set_dept_by_id(emp.department_id)

    def _save(self) -> None:
        self._clear_errors()
        q_date = self._date_edit.date()
        entry_date = date(q_date.year(), q_date.month(), q_date.day())
        uin = self._uin_edit.text().strip()
        name = self._name_edit.text().strip()
        dept_id = self._picker.selected_dept_id()
        code_id = self._picker.selected_code_id()
        hours = self._hours_spin.value()
        desc = self._desc_edit.toPlainText().strip()

        entry_id, errors = self._logging_svc.save_entry(
            uin=uin,
            name=name,
            department_id=dept_id or 0,
            activity_code_id=code_id or 0,
            entry_date=entry_date,
            hours=hours,
            description=desc,
        )

        if errors:
            self._show_errors(errors)
            return

        self._status_label.setText(f"Entry saved (id={entry_id}).")
        self._refresh_completers()
        self._refresh_today()
        # Sticky: keep dept and date; clear the variable fields
        self._uin_edit.clear()
        self._name_edit.clear()
        self._hours_spin.setValue(1.0)
        self._desc_edit.clear()

    def _clear(self) -> None:
        self._clear_errors()
        self._uin_edit.clear()
        self._name_edit.clear()
        self._hours_spin.setValue(1.0)
        self._desc_edit.clear()
        self._date_edit.setDate(QDate.currentDate())
        self._status_label.clear()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _clear_errors(self) -> None:
        for lbl in (self._uin_error, self._name_error, self._date_error,
                    self._code_error, self._hours_error):
            lbl.setVisible(False)
            lbl.clear()

    def _show_errors(self, errors) -> None:
        field_map = {
            "uin": self._uin_error,
            "name": self._name_error,
            "entry_date": self._date_error,
            "activity_code": self._code_error,
            "hours": self._hours_error,
        }
        for err in errors:
            lbl = field_map.get(err.field)
            if lbl:
                lbl.setText(err.message)
                lbl.setVisible(True)

    def _refresh_completers(self) -> None:
        employees = self._emp_repo.list_all()
        uins = [e.uin for e in employees]
        names = [e.name for e in employees]
        self._uin_completer.setModel(
            __import__("PySide6.QtCore", fromlist=["QStringListModel"]).QStringListModel(uins)
        )
        self._name_completer.setModel(
            __import__("PySide6.QtCore", fromlist=["QStringListModel"]).QStringListModel(names)
        )

    def _refresh_today(self) -> None:
        today = date.today()
        svc = AggregationService(self._conn)
        all_rows = svc.monthly_rows(today.year, today.month)
        self._today_model.load([r for r in all_rows if r.entry_date == today])
        self._today_table.resizeColumnsToContents()
