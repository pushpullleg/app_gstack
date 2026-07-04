"""QAbstractTableModel over a list of ReportCodeRow (per-code quarterly totals)."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from activity_logger.models.entities import ReportCodeRow

_HEADERS = ["Activity Code", "Description", "Total Hours"]


class AggregateModel(QAbstractTableModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[ReportCodeRow] = []
        self._grand_total: float = 0.0

    def load(self, rows: list[ReportCodeRow]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self._grand_total = round(sum(r.hours for r in rows), 2)
        self.endResetModel()

    def grand_total(self) -> float:
        return self._grand_total

    def rows(self) -> list[ReportCodeRow]:
        return list(self._rows)

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
                case 0: return r.code
                case 1: return r.description
                case 2: return f"{r.hours:.2f}"
        if role == Qt.TextAlignmentRole and col == 2:
            return int(Qt.AlignRight | Qt.AlignVCenter)
        return None
