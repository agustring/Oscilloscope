from __future__ import annotations

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from ..controller import OscilloscopeController
from .acquisition_panel import AcquisitionPanel
from .channel_panel import ChannelPanel
from .connection_panel import ConnectionPanel, DiagnosticsDialog
from .cursor_panel import CursorPanel
from .horizontal_panel import HorizontalPanel
from .measurement_panel import MeasurementPanel
from .scpi_console import ScpiConsole
from .trigger_panel import TriggerPanel
from .waveform_view import WaveformView


SCOPE_STEPS = (1.0, 2.0, 5.0)


def next_125(value: float, zoom_in: bool, minimum: float, maximum: float) -> float:
    if value <= 0:
        return minimum
    exponent = int(np.floor(np.log10(value)))
    candidates = sorted(
        step * 10.0**power
        for power in range(exponent - 2, exponent + 3)
        for step in SCOPE_STEPS
        if minimum <= step * 10.0**power <= maximum
    )
    if zoom_in:
        smaller = [item for item in candidates if item < value * (1 - 1e-9)]
        return smaller[-1] if smaller else minimum
    larger = [item for item in candidates if item > value * (1 + 1e-9)]
    return larger[0] if larger else maximum


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tektronix MSO2024 Remote")
        self.resize(1500, 950)
        self.controller = OscilloscopeController(self)
        self.connected = False
        self._build_ui()
        self._connect_signals()
        QtCore.QTimer.singleShot(250, self.controller.request_scan.emit)

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        self.connection_panel = ConnectionPanel()
        self.waveform = WaveformView()
        root.addWidget(self.connection_panel)
        root.addWidget(self.waveform, 4)
        controls = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.channel_panel = ChannelPanel()
        self.horizontal_panel = HorizontalPanel()
        self.acquisition_panel = AcquisitionPanel()
        self.trigger_panel = TriggerPanel()
        self.cursor_panel = CursorPanel()
        left = QtWidgets.QTabWidget()
        left.addTab(self.channel_panel, "Channels")
        left.addTab(self.horizontal_panel, "Horizontal")
        left.addTab(self.acquisition_panel, "Acquisition")
        right = QtWidgets.QTabWidget()
        right.addTab(self.trigger_panel, "Trigger")
        right.addTab(self.cursor_panel, "Cursors")
        controls.addWidget(left)
        controls.addWidget(right)
        controls.setSizes([850, 500])
        root.addWidget(controls, 2)
        self.measurements = MeasurementPanel()
        root.addWidget(self.measurements, 2)
        actions = QtWidgets.QHBoxLayout()
        self.run = QtWidgets.QPushButton("RUN")
        self.stop = QtWidgets.QPushButton("STOP")
        self.single = QtWidgets.QPushButton("SINGLE")
        self.autoset = QtWidgets.QPushButton("AUTOSET")
        self.save = QtWidgets.QPushButton("SAVE WAVEFORM")
        self.console_button = QtWidgets.QPushButton("SCPI CONSOLE")
        self.diagnostics_button = QtWidgets.QPushButton("DIAGNOSTICS")
        for button in (self.run, self.stop, self.single, self.autoset, self.save, self.console_button, self.diagnostics_button):
            actions.addWidget(button)
        actions.addStretch()
        root.addLayout(actions)
        self.setCentralWidget(central)
        self.scpi_console = ScpiConsole(self)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.scpi_console)
        self.scpi_console.hide()
        self.diagnostics_dialog = DiagnosticsDialog(self)
        self.statusBar().showMessage("Scan VISA resources to find an MSO2024")

    def _connect_signals(self) -> None:
        worker = self.controller.worker
        self.connection_panel.scan_requested.connect(self.controller.request_scan)
        self.connection_panel.connect_requested.connect(self.controller.request_connect)
        self.connection_panel.disconnect_requested.connect(self.controller.request_disconnect)
        self.connection_panel.timeout_changed.connect(self.controller.request_timeout)
        worker.resources_found.connect(self.connection_panel.set_resources)
        worker.connection_changed.connect(self._connection_changed)
        worker.waveform_ready.connect(self.waveform.update_waveform)
        worker.snapshot_ready.connect(self._apply_snapshot)
        worker.measurements_ready.connect(self.measurements.apply_measurements)
        worker.cursors_ready.connect(self._apply_cursors)
        worker.console_result.connect(self.scpi_console.append_result)
        worker.diagnostics.connect(self.diagnostics_dialog.update_diagnostics)
        worker.error.connect(self._error)
        worker.operation_done.connect(self._operation_done)
        for panel in (self.channel_panel, self.horizontal_panel, self.acquisition_panel, self.trigger_panel, self.measurements, self.cursor_panel):
            panel.changed.connect(self._invoke)
        self.channel_panel.selected.connect(self.waveform.select_channel)
        self.waveform.vertical_zoom.connect(self._vertical_zoom)
        self.waveform.horizontal_zoom.connect(self._horizontal_zoom)
        self.waveform.horizontal_pan.connect(self._horizontal_pan)
        self.waveform.reset_requested.connect(self._reset_view)
        self.waveform.cursor_moved.connect(lambda axis, number, value: self._invoke("set_cursor_position", [axis, number, value]))
        self.scpi_console.command_requested.connect(self.controller.request_console)
        self.diagnostics_dialog.events_requested.connect(self.controller.request_events)
        self.run.clicked.connect(lambda: self._invoke("run", []))
        self.stop.clicked.connect(lambda: self._invoke("stop", []))
        self.single.clicked.connect(lambda: self._invoke("single", []))
        self.autoset.clicked.connect(lambda: self._invoke("autoset", []))
        self.save.clicked.connect(self._save_waveform)
        self.console_button.clicked.connect(lambda: self.scpi_console.setVisible(not self.scpi_console.isVisible()))
        self.diagnostics_button.clicked.connect(self.diagnostics_dialog.show)

    @QtCore.Slot(str, object)
    def _invoke(self, method: str, arguments: object) -> None:
        if self.connected:
            self.controller.request_invoke.emit(method, arguments)

    def _connection_changed(self, connected: bool, identity: str, resource: str) -> None:
        self.connected = connected
        self.connection_panel.set_connected(connected, identity, resource)
        self.statusBar().showMessage(identity if connected else "Disconnected")

    def _apply_snapshot(self, snapshot: dict) -> None:
        self.channel_panel.apply_state(snapshot.get("channels", {}))
        self.horizontal_panel.apply_state(snapshot.get("horizontal", {}))
        self.acquisition_panel.apply_state(snapshot.get("acquisition", {}))
        self.trigger_panel.apply_state(snapshot.get("trigger", {}))
        for channel, state in snapshot.get("channels", {}).items():
            self.waveform.set_channel_visible(int(channel), state.get("enabled", False))

    def _apply_cursors(self, state: dict) -> None:
        self.cursor_panel.apply_state(state)
        self.waveform.set_cursor_state(state)

    def _vertical_zoom(self, channel: int, direction: int) -> None:
        control = self.channel_panel.controls[channel]["scale"]
        value = next_125(control.value(), direction > 0, 1e-6, 1e6)
        self._invoke("set_vertical_scale", [channel, value])

    def _horizontal_zoom(self, direction: int) -> None:
        value = next_125(self.horizontal_panel.scale.value(), direction > 0, 2e-9, 100.0)
        self._invoke("set_time_scale", [value])

    def _horizontal_pan(self, seconds: float) -> None:
        if self.connected:
            self._invoke("set_delay", [seconds])

    def _reset_view(self, channel: int) -> None:
        self._invoke("set_vertical_position", [channel, 0.0])
        self._invoke("set_horizontal_position", [50.0])

    def _save_waveform(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save waveform", f"CH{self.waveform.selected_channel}.csv", "CSV files (*.csv)"
        )
        if path:
            self.controller.request_export_waveform.emit(self.waveform.selected_channel, path)
            self.statusBar().showMessage("Downloading full-resolution waveform…")

    def _operation_done(self, name: str, result: object) -> None:
        if name == "all_events":
            self.diagnostics_dialog.append_events(str(result))
        elif name == "waveform_exported":
            self.statusBar().showMessage(
                f"Saved {result['points']} samples to {result['path']}", 8000
            )

    def _error(self, message: str) -> None:
        self.statusBar().showMessage(message, 12000)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.controller.close()
        super().closeEvent(event)
