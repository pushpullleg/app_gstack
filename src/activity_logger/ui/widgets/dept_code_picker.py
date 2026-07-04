"""Dept combo → filtered activity-code combo. Reused across views."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from activity_logger.repositories.activity_codes import ActivityCodeRepo
from activity_logger.repositories.departments import DepartmentRepo


class DeptCodePicker(QWidget):
    dept_changed = Signal(int)   # dept_id
    code_changed = Signal(int)   # activity_code_id

    def __init__(self, conn: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self._conn = conn
        self._dept_repo = DepartmentRepo(conn)
        self._code_repo = ActivityCodeRepo(conn)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        layout.addWidget(QLabel("Department:"))
        self._dept_combo = QComboBox()
        self._dept_combo.setMinimumWidth(180)
        layout.addWidget(self._dept_combo)

        layout.addSpacing(12)
        layout.addWidget(QLabel("Activity Code:"))
        self._code_combo = QComboBox()
        self._code_combo.setMinimumWidth(220)
        layout.addWidget(self._code_combo)

        layout.addStretch()

        self._dept_combo.currentIndexChanged.connect(self._on_dept_changed)
        self._load_depts()

    # ── public ────────────────────────────────────────────────────────────────

    def selected_dept_id(self) -> int | None:
        return self._dept_combo.currentData()

    def selected_code_id(self) -> int | None:
        return self._code_combo.currentData()

    def selected_dept_code(self) -> str | None:
        dept_id = self._dept_combo.currentData()
        if dept_id is None:
            return None
        for i in range(self._dept_combo.count()):
            if self._dept_combo.itemData(i) == dept_id:
                text = self._dept_combo.itemText(i)
                return text.split(" — ")[0]
        return None

    def set_dept_by_id(self, dept_id: int) -> None:
        for i in range(self._dept_combo.count()):
            if self._dept_combo.itemData(i) == dept_id:
                self._dept_combo.setCurrentIndex(i)
                return

    def set_code_by_id(self, code_id: int) -> None:
        for i in range(self._code_combo.count()):
            if self._code_combo.itemData(i) == code_id:
                self._code_combo.setCurrentIndex(i)
                return

    # ── private ───────────────────────────────────────────────────────────────

    def _load_depts(self) -> None:
        self._dept_combo.blockSignals(True)
        self._dept_combo.clear()
        for d in self._dept_repo.list_active():
            self._dept_combo.addItem(f"{d.code} — {d.name}", userData=d.id)
        self._dept_combo.blockSignals(False)
        self._reload_codes()

    def _on_dept_changed(self, _idx: int) -> None:
        self._reload_codes()
        dept_id = self._dept_combo.currentData()
        if dept_id is not None:
            self.dept_changed.emit(dept_id)

    def _reload_codes(self) -> None:
        self._code_combo.clear()
        dept_id = self._dept_combo.currentData()
        if dept_id is None:
            return
        for c in self._code_repo.list_by_department(dept_id):
            self._code_combo.addItem(f"{c.code} — {c.description}", userData=c.id)
        code_id = self._code_combo.currentData()
        if code_id is not None:
            self.code_changed.emit(code_id)
