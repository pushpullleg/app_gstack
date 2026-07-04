"""Main application window: QTabWidget with 3 tabs + File menu."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTabWidget,
)

from activity_logger.services.csv_io import export_csv, import_csv
from activity_logger.ui.views.entry_view import EntryView
from activity_logger.ui.views.monthly_view import MonthlyView
from activity_logger.ui.views.quarterly_view import QuarterlyView


class MainWindow(QMainWindow):
    def __init__(self, conn: sqlite3.Connection, cfg: dict, parent=None) -> None:
        super().__init__(parent)
        self._conn = conn
        self._cfg = cfg

        self.setWindowTitle("Federal Activity Logger")
        self.resize(960, 680)
        self.setMinimumSize(720, 500)

        # ── Tabs ──────────────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._entry_view = EntryView(conn, cfg)
        self._monthly_view = MonthlyView(conn)
        self._quarterly_view = QuarterlyView(conn, cfg)

        self._tabs.addTab(self._entry_view, "Log Entry")
        self._tabs.addTab(self._monthly_view, "Monthly Master")
        self._tabs.addTab(self._quarterly_view, "Quarterly Report")

        self.setCentralWidget(self._tabs)

        # Refresh dependent views when switching tabs
        self._tabs.currentChanged.connect(self._on_tab_changed)

        # ── File menu ─────────────────────────────────────────────────────────
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("Export entries to CSV…", self._export_csv)
        file_menu.addAction("Import entries from CSV…", self._import_csv)
        file_menu.addSeparator()
        file_menu.addAction("&Quit", self.close)

        self.statusBar().showMessage("Ready")

    # ── slots ─────────────────────────────────────────────────────────────────

    def _on_tab_changed(self, idx: int) -> None:
        if idx == 1:
            self._monthly_view._refresh()  # noqa: SLF001

    def _export_csv(self) -> None:
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Export entries to CSV", "", "CSV Files (*.csv)"
        )
        if not path_str:
            return
        count = export_csv(self._conn, Path(path_str))
        self.statusBar().showMessage(f"Exported {count} entries to {path_str}")
        QMessageBox.information(self, "Export Complete", f"Exported {count} entries.")

    def _import_csv(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Import entries from CSV", "", "CSV Files (*.csv)"
        )
        if not path_str:
            return
        result = import_csv(self._conn, Path(path_str))
        summary = (
            f"Import complete.\n\n"
            f"Inserted: {result.inserted}\n"
            f"Skipped (duplicate UUID): {result.skipped}"
        )
        if result.name_mismatches:
            mismatches = "\n".join(f"  {uin}: '{old}' ≠ '{new}'" for uin, old, new in result.name_mismatches)
            summary += f"\n\nName mismatches (not renamed):\n{mismatches}"
        if result.errors:
            summary += f"\n\nErrors ({len(result.errors)}):\n" + "\n".join(f"  {e}" for e in result.errors[:10])
        QMessageBox.information(self, "Import Complete", summary)
        if result.inserted > 0:
            self._monthly_view._refresh()  # noqa: SLF001
