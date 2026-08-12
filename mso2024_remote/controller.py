from __future__ import annotations

from PySide6 import QtCore

from .workers.instrument_worker import InstrumentWorker


class OscilloscopeController(QtCore.QObject):
    """GUI-side bridge to the VISA-owning worker thread."""

    request_scan = QtCore.Signal()
    request_connect = QtCore.Signal(str, int)
    request_disconnect = QtCore.Signal()
    request_timeout = QtCore.Signal(int)
    request_invoke = QtCore.Signal(str, object)
    request_console = QtCore.Signal(str)
    request_events = QtCore.Signal()
    request_full_waveform = QtCore.Signal(int)
    request_export_waveform = QtCore.Signal(int, str)
    request_shutdown = QtCore.Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.thread = QtCore.QThread(self)
        self.worker = InstrumentWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.initialize)
        self.request_scan.connect(self.worker.scan)
        self.request_connect.connect(self.worker.connect_resource)
        self.request_disconnect.connect(self.worker.disconnect_resource)
        self.request_timeout.connect(self.worker.set_timeout)
        self.request_invoke.connect(self.worker.invoke)
        self.request_console.connect(self.worker.console)
        self.request_events.connect(self.worker.query_events)
        self.request_full_waveform.connect(self.worker.acquire_full_waveform)
        self.request_export_waveform.connect(self.worker.export_waveform)
        self.request_shutdown.connect(self.worker.shutdown)
        self.thread.start()

    def invoke(self, method: str, *args) -> None:
        self.request_invoke.emit(method, list(args))

    def close(self) -> None:
        self.request_shutdown.emit()
        self.thread.quit()
        self.thread.wait(3000)
