from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class CursorPanel(QtWidgets.QWidget):
    changed = QtCore.Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        form = QtWidgets.QFormLayout(self)
        self.function = QtWidgets.QComboBox()
        self.function.addItem("Off", "OFF")
        self.function.addItem("Time bars", "VBARS")
        self.function.addItem("Voltage bars", "HBARS")
        self.function.addItem("Screen (both)", "SCREEN")
        self.p1 = QtWidgets.QDoubleSpinBox()
        self.p2 = QtWidgets.QDoubleSpinBox()
        for spin in (self.p1, self.p2):
            spin.setDecimals(9)
            spin.setRange(-1e6, 1e6)
            spin.setKeyboardTracking(False)
        self.delta = QtWidgets.QLabel("—")
        self.inverse = QtWidgets.QLabel("—")
        form.addRow("Cursors", self.function)
        form.addRow("Cursor 1", self.p1)
        form.addRow("Cursor 2", self.p2)
        form.addRow("Δ", self.delta)
        form.addRow("1 / ΔX", self.inverse)
        self.function.currentIndexChanged.connect(self._function_changed)
        self.p1.valueChanged.connect(lambda value: self._position_changed(1, value))
        self.p2.valueChanged.connect(lambda value: self._position_changed(2, value))
        self._function_changed()

    def _function_changed(self, *_args) -> None:
        function = self.function.currentData()
        self.changed.emit("set_cursor_function", [function])
        enabled = function != "OFF"
        self.p1.setEnabled(enabled)
        self.p2.setEnabled(enabled)
        suffix = " s" if function in {"VBARS", "SCREEN"} else " V"
        self.p1.setSuffix(suffix)
        self.p2.setSuffix(suffix)

    def _position_changed(self, number: int, value: float) -> None:
        function = self.function.currentData()
        axis = "VBARS" if function in {"VBARS", "SCREEN"} else "HBARS"
        self.changed.emit("set_cursor_position", [axis, number, value])

    def apply_state(self, state: dict) -> None:
        function = state.get("function", "OFF")
        index = self.function.findData(function)
        if index >= 0:
            blocker = QtCore.QSignalBlocker(self.function)
            self.function.setCurrentIndex(index)
            del blocker
        horizontal = function in {"VBARS", "SCREEN"}
        for spin, key in ((self.p1, "x1" if horizontal else "y1"), (self.p2, "x2" if horizontal else "y2")):
            blocker = QtCore.QSignalBlocker(spin)
            spin.setValue(float(state.get(key, 0.0)))
            del blocker
        delta = state.get("dx" if horizontal else "dy")
        self.delta.setText("—" if delta is None else f"{float(delta):.8g}")
        self.inverse.setText("—" if not horizontal or not delta else f"{1.0 / float(delta):.8g} Hz")
        self._set_suffix(function)

    def _set_suffix(self, function: str) -> None:
        suffix = " s" if function in {"VBARS", "SCREEN"} else " V"
        self.p1.setSuffix(suffix)
        self.p2.setSuffix(suffix)
