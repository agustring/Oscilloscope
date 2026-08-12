from __future__ import annotations

import math

from PySide6 import QtCore, QtWidgets

from ..instrument.mso2024 import MEASUREMENT_TYPES


TYPE_BY_CODE = {code: label for label, code in MEASUREMENT_TYPES.items()}


def engineering(value: float, unit: str = "") -> str:
    if not math.isfinite(value) or abs(value) >= 9.9e36:
        return "—"
    prefixes = [(1e9, "G"), (1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m"), (1e-6, "µ"), (1e-9, "n"), (1e-12, "p")]
    magnitude = abs(value)
    for factor, prefix in prefixes:
        if magnitude >= factor or factor == 1e-12:
            return f"{value / factor:.6g} {prefix}{unit}"
    return f"{value:.6g} {unit}"


class MeasurementPanel(QtWidgets.QWidget):
    changed = QtCore.Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        configure = QtWidgets.QHBoxLayout()
        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems(MEASUREMENT_TYPES.keys())
        self.type_combo.setCurrentText("Frequency")
        self.source_combo = QtWidgets.QComboBox()
        self.source_combo.addItems(["CH1", "CH2", "CH3", "CH4", "MATH1", "REF1", "REF2"])
        self.source2_combo = QtWidgets.QComboBox()
        self.source2_combo.addItems(["CH1", "CH2", "CH3", "CH4", "MATH1", "REF1", "REF2"])
        self.source2_combo.setCurrentText("CH2")
        self.add_button = QtWidgets.QPushButton("Add")
        self.remove_button = QtWidgets.QPushButton("Remove")
        configure.addWidget(self.type_combo, 2)
        configure.addWidget(self.source_combo)
        configure.addWidget(self.source2_combo)
        configure.addWidget(self.add_button)
        configure.addWidget(self.remove_button)
        self.table = QtWidgets.QTableWidget(4, 4)
        self.table.setHorizontalHeaderLabels(["Slot", "Measurement", "Source", "Value"])
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        for row in range(4):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(row + 1)))
            for column in range(1, 4):
                self.table.setItem(row, column, QtWidgets.QTableWidgetItem("—"))
        layout.addLayout(configure)
        layout.addWidget(self.table)
        self.add_button.clicked.connect(self._add)
        self.remove_button.clicked.connect(self._remove)
        self.type_combo.currentTextChanged.connect(self._type_changed)
        self._type_changed(self.type_combo.currentText())

    def _type_changed(self, label: str) -> None:
        self.source2_combo.setVisible(label in {"Delay", "Phase"})
        self.source2_combo.setToolTip("Second (to/reference) source for Delay and Phase")

    def _available_slot(self) -> int | None:
        selected = self.table.currentRow()
        if selected >= 0 and self.table.item(selected, 1).text() == "—":
            return selected + 1
        for row in range(4):
            if self.table.item(row, 1).text() == "—":
                return row + 1
        return None

    def _add(self) -> None:
        slot = self._available_slot()
        if slot is None:
            QtWidgets.QToolTip.showText(self.add_button.mapToGlobal(self.add_button.rect().bottomLeft()), "All four hardware measurement slots are in use")
            return
        self.changed.emit(
            "configure_measurement",
            [
                slot,
                MEASUREMENT_TYPES[self.type_combo.currentText()],
                self.source_combo.currentText(),
                True,
                self.source2_combo.currentText(),
            ],
        )

    def _remove(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.changed.emit("disable_measurement", [row + 1])

    def apply_measurements(self, states: list[dict]) -> None:
        for state in states:
            row = int(state["slot"]) - 1
            if not state.get("enabled"):
                values = ("—", "—", "—")
            else:
                values = (
                    TYPE_BY_CODE.get(state.get("type", ""), state.get("type", "")),
                    state.get("source", "—"),
                    engineering(float(state.get("value", math.nan)), state.get("unit", "")),
                )
            for column, value in enumerate(values, start=1):
                self.table.item(row, column).setText(str(value))
