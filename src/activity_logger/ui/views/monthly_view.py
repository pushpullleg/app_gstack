"""Monthly Master tab — filterable grid of all entries for a month."""

from __future__ import annotations

import sqlite3
from datetime import date

from PySide6.QtCore import QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QDate

from activity_logger.repositories.activity_codes import ActivityCodeRepo
from activity_logger.repositories.departments import DepartmentRepo
from activity_logger.repositories.log_entries import LogEntryRepo
from activity_logger.services.aggregation_service import AggregationService, MonthlyRow
from activity_logger.services.logging_service import LoggingService
from activity_logger.ui.models_qt.log_table_model import LogTableModel
from activity_logger.ui.widgets.dept_code_picker import DeptCodePicker


class _MonthlyFilter(QSortFilterProxyModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._dept_filter = ""
        self._text_filter = ""
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)

    def set_dept(self, dept_code: str) -> None:
        self._dept_filter = dept_code
        self.invalidateFilter()

    def set_text(self, text: str) -> None:
        self._text_filter = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        def _col(c: int) -> str:
            idx = self.sourceModel().index(source_row, c, source_parent)
            return self.sourceModel().data(idx, Qt.DisplayRole) or ""

        if self._dept_filter and _col(3) != self._dept_filter:
            return False
        if self._text_filter:
            uin = _col(1).lower()
            name = _col(2).lower()
            if self._text_filter not in uin and self._text_filter not in name:
                return False
        return True


class _EditDialog(QDialog):
    """Minimal edit dialog for changing hours, code, and description."""

    def __init__(self, conn: sqlite3.Connection, row: MonthlyRow, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Entry")
        self._conn = conn
        self._row = row
        self._svc = LoggingService(conn)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Date (read-only)
        date_lbl = QLabel(str(row.entry_date))
        form.addRow("Date:", date_lbl)
        form.addRow("Employee:", QLabel(f"{row.employee_uin} — {row.employee_name}"))

        # Dept / Code
        self._picker = DeptCodePicker(conn)
        # Pre-select the current code
        code_repo = ActivityCodeRepo(conn)
        code = code_repo.get_by_code(row.activity_code)
        if code:
            self._picker.set_dept_by_id(code.department_id)
            self._picker.set_code_by_id(code.id)
        form.addRow("Code:", self._picker)

        # Hours
        self._hours_spin = QDoubleSpinBox()
        self._hours_spin.setRange(0.25, 24.0)
        self._hours_spin.setSingleStep(0.25)
        self._hours_spin.setDecimals(2)
        self._hours_spin.setValue(row.hours)
        self._hours_spin.setSuffix(" hrs")
        form.addRow("Hours:", self._hours_spin)

        # Description
        from PySide6.QtWidgets import QPlainTextEdit
        self._desc_edit = QPlainTextEdit(row.description)
        self._desc_edit.setMaximumHeight(60)
        form.addRow("Description:", self._desc_edit)

        layout.addLayout(form)

        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._do_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(420, 280)

    def _do_save(self) -> None:
        code_id = self._picker.selected_code_id()
        hours = self._hours_spin.value()
        desc = self._desc_edit.toPlainText().strip()
        errors = self._svc.update_entry(
            self._row.entry_id,
            hours=hours,
            activity_code_id=code_id or 0,
            description=desc,
        )
        if errors:
            self._error_label.setText("; ".join(e.message for e in errors))
            self._error_label.setVisible(True)
            return
        self.accept()


class MonthlyView(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self._conn = conn
        today = date.today()
        self._year = today.year
        self._month = today.month

        self._model = LogTableModel()
        self._proxy = _MonthlyFilter()
        self._proxy.setSourceModel(self._model)

        self._build_ui()
        self._refresh()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(6)

        # ── Month stepper ─────────────────────────────────────────────────────
        stepper_row = QHBoxLayout()
        self._prev_btn = QPushButton("◀")
        self._prev_btn.setFixedWidth(32)
        self._prev_btn.clicked.connect(self._prev_month)
        self._month_label = QLabel()
        self._month_label.setAlignment(Qt.AlignCenter)
        self._month_label.setMinimumWidth(160)
        self._month_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        self._next_btn = QPushButton("▶")
        self._next_btn.setFixedWidth(32)
        self._next_btn.clicked.connect(self._next_month)
        stepper_row.addWidget(self._prev_btn)
        stepper_row.addWidget(self._month_label)
        stepper_row.addWidget(self._next_btn)
        stepper_row.addStretch()
        root.addLayout(stepper_row)

        # ── Filter bar ────────────────────────────────────────────────────────
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Dept:"))
        self._dept_filter_combo = QComboBox()
        self._dept_filter_combo.addItem("All", userData="")
        dept_repo = DepartmentRepo(self._conn)
        for d in dept_repo.list_active():
            self._dept_filter_combo.addItem(d.code, userData=d.code)
        self._dept_filter_combo.currentIndexChanged.connect(
            lambda _: self._proxy.set_dept(self._dept_filter_combo.currentData() or "")
        )
        filter_row.addWidget(self._dept_filter_combo)
        filter_row.addSpacing(16)
        filter_row.addWidget(QLabel("Search:"))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("UIN or name…")
        self._search_edit.setMaximumWidth(200)
        self._search_edit.textChanged.connect(self._proxy.set_text)
        filter_row.addWidget(self._search_edit)
        filter_row.addStretch()
        root.addLayout(filter_row)

        # ── Table ─────────────────────────────────────────────────────────────
        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._context_menu)
        self._table.doubleClicked.connect(self._edit_selected)
        root.addWidget(self._table)

        self._status_label = QLabel()
        root.addWidget(self._status_label)

        self._update_month_label()

    # ── slots ─────────────────────────────────────────────────────────────────

    def _prev_month(self) -> None:
        if self._month == 1:
            self._year -= 1
            self._month = 12
        else:
            self._month -= 1
        self._refresh()

    def _next_month(self) -> None:
        if self._month == 12:
            self._year += 1
            self._month = 1
        else:
            self._month += 1
        self._refresh()

    def _context_menu(self, pos) -> None:
        idx = self._table.indexAt(pos)
        if not idx.isValid():
            return
        menu = QMenu(self)
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == edit_action:
            self._edit_at_proxy_index(idx)
        elif action == delete_action:
            self._delete_at_proxy_index(idx)

    def _edit_selected(self, idx: QModelIndex) -> None:
        self._edit_at_proxy_index(idx)

    def _edit_at_proxy_index(self, proxy_idx: QModelIndex) -> None:
        src_idx = self._proxy.mapToSource(proxy_idx)
        row = self._model.row_at(src_idx.row())
        dlg = _EditDialog(self._conn, row, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._refresh()

    def _delete_at_proxy_index(self, proxy_idx: QModelIndex) -> None:
        src_idx = self._proxy.mapToSource(proxy_idx)
        row = self._model.row_at(src_idx.row())
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete entry for {row.employee_uin} on {row.entry_date} ({row.activity_code}, {row.hours:.2f} hrs)?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            svc = LoggingService(self._conn)
            svc.delete_entry(row.entry_id)
            self._refresh()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        svc = AggregationService(self._conn)
        rows = svc.monthly_rows(self._year, self._month)
        self._model.load(rows)
        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setStretchLastSection(True)
        self._update_month_label()
        count = self._proxy.rowCount()
        self._status_label.setText(f"{count} entries" if rows else "No entries for this month.")

    def _update_month_label(self) -> None:
        import calendar
        month_name = calendar.month_name[self._month]
        self._month_label.setText(f"{month_name} {self._year}")
