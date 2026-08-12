from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class HorizontalPanel(QtWidgets.QWidget):
    changed = QtCore.Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        form = QtWidgets.QFormLayout(self)
        self.scale = QtWidgets.QDoubleSpinBox()
        self.scale.setDecimals(9)
        self.scale.setRange(2e-9, 100.0)
        self.scale.setValue(1e-3)
        self.scale.setSuffix(" s/div")
        self.scale.setKeyboardTracking(False)
        self.position = QtWidgets.QDoubleSpinBox()
        self.position.setRange(0, 100)
        self.position.setValue(50)
        self.position.setSuffix(" %")
        self.position.setKeyboardTracking(False)
        self.delay = QtWidgets.QDoubleSpinBox()
        self.delay.setDecimals(9)
        self.delay.setRange(-1e6, 1e6)
        self.delay.setSuffix(" s")
        self.delay.setKeyboardTracking(False)
        self.record = QtWidgets.QComboBox()
        self.record.addItems(["100000", "1000000"])
        form.addRow("Time / division", self.scale)
        form.addRow("Trigger position", self.position)
        form.addRow("Delay", self.delay)
        form.addRow("Record length", self.record)
        self.scale.valueChanged.connect(lambda value: self.changed.emit("set_time_scale", [value]))
        self.position.valueChanged.connect(lambda value: self.changed.emit("set_horizontal_position", [value]))
        self.delay.valueChanged.connect(lambda value: self.changed.emit("set_delay", [value]))
        self.record.currentTextChanged.connect(lambda value: self.changed.emit("set_record_length", [int(value)]))

    def apply_state(self, state: dict) -> None:
        for widget, value in (
            (self.scale, state.get("scale", 1e-3)),
            (self.position, state.get("position", 50.0)),
            (self.delay, state.get("delay", 0.0)),
        ):
            blocker = QtCore.QSignalBlocker(widget)
            widget.setValue(float(value))
            del blocker
        blocker = QtCore.QSignalBlocker(self.record)
        self.record.setCurrentText(str(int(state.get("record_length", 100000))))
        del blocker
