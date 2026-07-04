"""QAbstractTableModel over a list of MonthlyRow (the joined log entry query)."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from activity_logger.services.aggregation_service import MonthlyRow

_HEADERS = ["Date", "UIN", "Name", "Dept", "Code", "Hours", "Description"]


class LogTableModel(QAbstractTableModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[MonthlyRow] = []

    def load(self, rows: list[MonthlyRow]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def row_at(self, idx: int) -> MonthlyRow:
        return self._rows[idx]

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(_HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):  # noqa: N802
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return _HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        r = self._rows[index.row()]
        col = index.column()
        if role == Qt.DisplayRole:
            match col:
                case 0: return str(r.entry_date)
                case 1: return r.employee_uin
                case 2: return r.employee_name
                case 3: return r.department_code
                case 4: return r.activity_code
                case 5: return f"{r.hours:.2f}"
                case 6: return r.description
        if role == Qt.TextAlignmentRole and col == 5:
            return int(Qt.AlignRight | Qt.AlignVCenter)
        return None
