from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class ConnectionPanel(QtWidgets.QWidget):
    scan_requested = QtCore.Signal()
    connect_requested = QtCore.Signal(str, int)
    disconnect_requested = QtCore.Signal()
    timeout_changed = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QGridLayout(self)
        self.resources = QtWidgets.QComboBox()
        self.resources.setMinimumWidth(420)
        self.scan_button = QtWidgets.QPushButton("Scan VISA")
        self.connect_button = QtWidgets.QPushButton("Connect")
        self.disconnect_button = QtWidgets.QPushButton("Disconnect")
        self.timeout = QtWidgets.QSpinBox()
        self.timeout.setRange(500, 120000)
        self.timeout.setValue(5000)
        self.timeout.setSuffix(" ms")
        self.status = QtWidgets.QLabel("Disconnected")
        self.status.setProperty("state", "off")
        layout.addWidget(QtWidgets.QLabel("Instrument"), 0, 0)
        layout.addWidget(self.resources, 0, 1, 1, 4)
        layout.addWidget(self.scan_button, 0, 5)
        layout.addWidget(QtWidgets.QLabel("VISA timeout"), 1, 0)
        layout.addWidget(self.timeout, 1, 1)
        layout.addWidget(self.connect_button, 1, 2)
        layout.addWidget(self.disconnect_button, 1, 3)
        layout.addWidget(self.status, 1, 4, 1, 2)
        self.scan_button.clicked.connect(self.scan_requested)
        self.connect_button.clicked.connect(self._connect)
        self.disconnect_button.clicked.connect(self.disconnect_requested)
        self.timeout.valueChanged.connect(self.timeout_changed)
        self.set_connected(False)

    def _connect(self) -> None:
        resource = self.resources.currentData()
        if resource:
            self.connect_requested.emit(resource, self.timeout.value())

    def set_resources(self, resources: list[dict]) -> None:
        self.resources.clear()
        for item in resources:
            identity = item.get("identity") or item.get("error") or "No response"
            prefix = "MSO2024 · " if item.get("is_mso2024") else ""
            self.resources.addItem(f"{prefix}{item['resource']} — {identity}", item["resource"])

    def set_connected(self, connected: bool, identity: str = "", resource: str = "") -> None:
        self.connect_button.setEnabled(not connected)
        self.disconnect_button.setEnabled(connected)
        self.resources.setEnabled(not connected)
        self.scan_button.setEnabled(not connected)
        self.status.setText(f"Connected · {identity}" if connected else "Disconnected")
        self.status.setProperty("state", "on" if connected else "off")
        self.style().unpolish(self.status)
        self.style().polish(self.status)


class DiagnosticsDialog(QtWidgets.QDialog):
    events_requested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Diagnostics")
        self.resize(680, 420)
        layout = QtWidgets.QVBoxLayout(self)
        self.fields = QtWidgets.QFormLayout()
        self.labels: dict[str, QtWidgets.QLabel] = {}
        for key, title in (
            ("connected", "Connection"),
            ("resource", "Resource"),
            ("identity", "Identity"),
            ("last_command", "Last command"),
            ("last_response", "Last response"),
            ("error", "Last communication error"),
        ):
            label = QtWidgets.QLabel("—")
            label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
            label.setWordWrap(True)
            self.fields.addRow(title, label)
            self.labels[key] = label
        buttons = QtWidgets.QHBoxLayout()
        query = QtWidgets.QPushButton("Read Tektronix event queue")
        query.clicked.connect(self.events_requested)
        buttons.addWidget(query)
        buttons.addStretch()
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addLayout(self.fields)
        layout.addLayout(buttons)
        layout.addWidget(self.log)

    def update_diagnostics(self, data: dict) -> None:
        for key, label in self.labels.items():
            value = data.get(key, "")
            if key == "connected":
                value = "Connected" if value else "Disconnected"
            label.setText(str(value or "—"))
        if data.get("error"):
            self.log.appendPlainText(f"[{data.get('timestamp', '')}] VISA · {data['error']}")

    def append_events(self, events: str) -> None:
        self.log.appendPlainText(f"Tektronix events · {events}")
