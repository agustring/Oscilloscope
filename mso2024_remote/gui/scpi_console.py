from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


class HistoryLineEdit(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history: list[str] = []
        self.history_index = 0

    def remember(self, command: str) -> None:
        if command and (not self.history or self.history[-1] != command):
            self.history.append(command)
        self.history_index = len(self.history)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() in (QtCore.Qt.Key.Key_Up, QtCore.Qt.Key.Key_Down) and self.history:
            step = -1 if event.key() == QtCore.Qt.Key.Key_Up else 1
            self.history_index = max(0, min(len(self.history), self.history_index + step))
            self.setText("" if self.history_index == len(self.history) else self.history[self.history_index])
            return
        super().keyPressEvent(event)


class ScpiConsole(QtWidgets.QDockWidget):
    command_requested = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__("SCPI Console", parent)
        self.setObjectName("scpiConsole")
        body = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(body)
        self.output = QtWidgets.QPlainTextEdit()
        self.output.setReadOnly(True)
        self.input = HistoryLineEdit()
        self.input.setPlaceholderText("*IDN?   ·   CH1:SCALE?   ·   HOR:SCALE?")
        send = QtWidgets.QPushButton("Send")
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.input, 1)
        row.addWidget(send)
        layout.addWidget(self.output)
        layout.addLayout(row)
        self.setWidget(body)
        send.clicked.connect(self._send)
        self.input.returnPressed.connect(self._send)

    def _send(self) -> None:
        command = self.input.text().strip()
        if command:
            self.input.remember(command)
            self.command_requested.emit(command)
            self.input.clear()

    def append_result(self, command: str, response: str, ok: bool) -> None:
        self.output.appendPlainText(f"> {command}\n{'< ' if ok else '! '}{response}\n")
