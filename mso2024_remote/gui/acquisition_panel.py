from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class AcquisitionPanel(QtWidgets.QWidget):
    changed = QtCore.Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        buttons = QtWidgets.QHBoxLayout()
        self.run_button = QtWidgets.QPushButton("RUN")
        self.stop_button = QtWidgets.QPushButton("STOP")
        self.single_button = QtWidgets.QPushButton("SINGLE")
        for button in (self.run_button, self.stop_button, self.single_button):
            buttons.addWidget(button)
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(["SAMPLE", "AVERAGE"])
        self.averages = QtWidgets.QComboBox()
        self.averages.addItems([str(2**power) for power in range(1, 10)])
        note = QtWidgets.QLabel(
            "The MSO2000 programmer manual documents SAMPLE and AVERAGE for ACQUIRE:MODE; "
            "Peak Detect, Envelope, and Hi-Res are therefore not sent."
        )
        note.setWordWrap(True)
        note.setProperty("class", "note")
        form = QtWidgets.QFormLayout()
        form.addRow("Mode", self.mode)
        form.addRow("Average count", self.averages)
        layout.addLayout(buttons)
        layout.addLayout(form)
        layout.addWidget(note)
        self.run_button.clicked.connect(lambda: self.changed.emit("run", []))
        self.stop_button.clicked.connect(lambda: self.changed.emit("stop", []))
        self.single_button.clicked.connect(lambda: self.changed.emit("single", []))
        self.mode.currentTextChanged.connect(self._mode_changed)
        self.averages.currentTextChanged.connect(self._mode_changed)
        self._mode_changed()

    def _mode_changed(self, *_args) -> None:
        average = self.mode.currentText() == "AVERAGE"
        self.averages.setEnabled(average)
        self.changed.emit(
            "set_acquisition_mode",
            [self.mode.currentText(), int(self.averages.currentText()) if average else None],
        )

    def apply_state(self, state: dict) -> None:
        for widget, value in (
            (self.mode, state.get("mode", "SAMPLE")),
            (self.averages, str(state.get("averages", 16))),
        ):
            blocker = QtCore.QSignalBlocker(widget)
            widget.setCurrentText(value)
            del blocker
        self.averages.setEnabled(self.mode.currentText() == "AVERAGE")
        running = bool(state.get("running", False))
        self.run_button.setProperty("active", running)
        self.stop_button.setProperty("active", not running)
        self.style().unpolish(self.run_button)
        self.style().polish(self.run_button)
        self.style().unpolish(self.stop_button)
        self.style().polish(self.stop_button)
