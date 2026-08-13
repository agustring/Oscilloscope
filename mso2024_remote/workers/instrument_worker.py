from __future__ import annotations

import time
import traceback
from typing import Any

import numpy as np
from PySide6 import QtCore

from ..instrument.mso2024 import TektronixMSO2024
from ..instrument.visa_connection import VisaConnection


class InstrumentWorker(QtCore.QObject):
    resources_found = QtCore.Signal(object)
    connection_changed = QtCore.Signal(bool, str, str)
    waveform_ready = QtCore.Signal(int, object, object, object)
    snapshot_ready = QtCore.Signal(object)
    measurements_ready = QtCore.Signal(object)
    cursors_ready = QtCore.Signal(object)
    console_result = QtCore.Signal(str, str, bool)
    diagnostics = QtCore.Signal(object)
    operation_done = QtCore.Signal(str, object)
    error = QtCore.Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.connection: VisaConnection | None = None
        self.scope: TektronixMSO2024 | None = None
        self.poll_timer: QtCore.QTimer | None = None
        self.poll_count = 0
        self.next_channel = 1
        self.enabled_channels = {1}
        self.busy = False
        self.last_transfer_ms = 0.0
        self.waveform_points = 0
        self.acquisition_rate = 0.0
        self._rate_started = time.perf_counter()
        self._rate_count = 0

    @QtCore.Slot()
    def initialize(self) -> None:
        self.connection = VisaConnection()
        self.scope = TektronixMSO2024(self.connection)
        self.poll_timer = QtCore.QTimer(self)
        self.poll_timer.setInterval(250)
        self.poll_timer.timeout.connect(self._poll)
        self.poll_timer.start()

    def _report_error(self, context: str, exc: Exception) -> None:
        detail = f"{context}: {exc}"
        self.error.emit(detail)
        self._emit_diagnostics(error=detail)

    def _emit_diagnostics(self, error: str = "") -> None:
        scope = self.scope
        connection = self.connection
        self.diagnostics.emit(
            {
                "connected": bool(connection and connection.connected),
                "resource": connection.resource_name if connection else "",
                "identity": connection.identity if connection else "",
                "last_command": scope.last_command if scope else "",
                "last_response": scope.last_response if scope else "",
                "error": error,
                "timestamp": time.strftime("%H:%M:%S"),
                "scpi_queue": 1 if self.busy else 0,
                "acquisition_rate": self.acquisition_rate,
                "waveform_points": self.waveform_points,
                "transfer_ms": self.last_transfer_ms,
            }
        )

    @QtCore.Slot(int)
    def set_timeout(self, timeout_ms: int) -> None:
        if self.connection:
            self.connection.set_timeout(timeout_ms)

    @QtCore.Slot()
    def scan(self) -> None:
        if not self.connection or self.busy:
            return
        self.busy = True
        try:
            records = self.connection.discover()
            self.resources_found.emit(
                [
                    {
                        "resource": item.resource,
                        "identity": item.identity,
                        "error": item.error,
                        "is_mso2024": item.is_mso2024,
                    }
                    for item in records
                ]
            )
        except Exception as exc:
            self._report_error("VISA discovery failed", exc)
        finally:
            self.busy = False

    @QtCore.Slot(str, int)
    def connect_resource(self, resource: str, timeout_ms: int) -> None:
        if not self.connection or self.busy:
            return
        self.busy = True
        try:
            self.connection.set_timeout(timeout_ms)
            identity = self.connection.connect(resource)
            self.connection_changed.emit(True, identity, resource)
            self._emit_diagnostics()
            self.poll_count = 0  # request a complete sync on the next timer tick
        except Exception as exc:
            self.connection_changed.emit(False, "", resource)
            self._report_error("Connection failed", exc)
        finally:
            self.busy = False

    @QtCore.Slot()
    def disconnect_resource(self) -> None:
        if not self.connection:
            return
        try:
            self.connection.disconnect()
        except Exception as exc:
            self._report_error("Disconnect failed", exc)
        self.connection_changed.emit(False, "", "")
        self._emit_diagnostics()

    def _require_scope(self) -> TektronixMSO2024:
        if not self.scope or not self.connection or not self.connection.connected:
            raise RuntimeError("Oscilloscope is not connected")
        return self.scope

    @QtCore.Slot(str, object)
    def invoke(self, method: str, arguments: object) -> None:
        if self.busy:
            return
        self.busy = True
        try:
            scope = self._require_scope()
            function = getattr(scope, method, None)
            if function is None or method.startswith("_"):
                raise AttributeError(f"Unknown instrument operation: {method}")
            args = list(arguments or [])
            result = function(*args)
            self.operation_done.emit(method, result)
            self._emit_diagnostics()
            if method.startswith("set_") or method in {"autoset", "run", "stop", "single"}:
                self.poll_count = 0
            if method == "set_channel_enabled" and len(args) >= 2:
                channel, enabled = int(args[0]), bool(args[1])
                (self.enabled_channels.add if enabled else self.enabled_channels.discard)(channel)
        except Exception as exc:
            self._report_error(method, exc)
            if self.connection and self.connection.connected:
                self.poll_count = 0
        finally:
            self.busy = False

    @QtCore.Slot(str)
    def console(self, command: str) -> None:
        if self.busy:
            return
        self.busy = True
        try:
            scope = self._require_scope()
            command = command.strip()
            if not command:
                return
            if "?" in command:
                response = scope.query(command)
            else:
                scope.write(command)
                response = "OK"
            self.console_result.emit(command, response, True)
            self._emit_diagnostics()
            self.poll_count = 3
        except Exception as exc:
            self.console_result.emit(command, str(exc), False)
            self._report_error("SCPI console", exc)
        finally:
            self.busy = False

    @QtCore.Slot()
    def query_events(self) -> None:
        try:
            response = self._require_scope().all_events()
            self.operation_done.emit("all_events", response)
            self._emit_diagnostics()
        except Exception as exc:
            self._report_error("Tektronix event queue", exc)

    @QtCore.Slot(int)
    def acquire_full_waveform(self, channel: int) -> None:
        if self.busy:
            return
        self.busy = True
        try:
            waveform = self._require_scope().save_waveform_data(channel)
            self.operation_done.emit("full_waveform", waveform)
            self._emit_diagnostics()
        except Exception as exc:
            self._report_error("Full-resolution waveform transfer", exc)
        finally:
            self.busy = False

    @QtCore.Slot(int, str)
    def export_waveform(self, channel: int, path: str) -> None:
        if self.busy:
            return
        self.busy = True
        try:
            waveform = self._require_scope().save_waveform_data(channel)
            data = np.column_stack((waveform.time, waveform.voltage))
            np.savetxt(path, data, delimiter=",", header="time_s,voltage_V", comments="")
            self.operation_done.emit("waveform_exported", {"path": path, "points": len(waveform.time)})
            self._emit_diagnostics()
        except Exception as exc:
            self._report_error("Waveform export", exc)
        finally:
            self.busy = False

    @QtCore.Slot()
    def _poll(self) -> None:
        if self.busy or not self.connection or not self.connection.connected:
            return
        self.busy = True
        try:
            scope = self._require_scope()
            # Transfer one enabled analog channel per tick to bound USB traffic.
            for _ in range(4):
                channel = self.next_channel
                self.next_channel = channel % 4 + 1
                if channel in self.enabled_channels:
                    transfer_started = time.perf_counter()
                    waveform = scope.waveform(channel, assume_enabled=True)
                    self.last_transfer_ms = (time.perf_counter() - transfer_started) * 1000.0
                    self.waveform_points = len(waveform.time)
                    self._rate_count += 1
                    elapsed = time.perf_counter() - self._rate_started
                    if elapsed >= 1.0:
                        self.acquisition_rate = self._rate_count / elapsed
                        self._rate_count, self._rate_started = 0, time.perf_counter()
                    self.waveform_ready.emit(
                        channel, waveform.time, waveform.voltage, waveform.preamble
                    )
                    break
            if self.poll_count % 4 == 0:
                measurements = [scope.measurement_state(slot) for slot in range(1, 5)]
                self.measurements_ready.emit(measurements)
            if self.poll_count % 8 == 0:
                self.cursors_ready.emit(scope.cursor_state())
            if self.poll_count % 12 == 0:
                snapshot = scope.snapshot()
                self.enabled_channels = {
                    int(channel)
                    for channel, state in snapshot["channels"].items()
                    if state.get("enabled")
                }
                self.snapshot_ready.emit(snapshot)
            self.poll_count += 1
            self._emit_diagnostics()
        except Exception as exc:
            self._report_error("Polling", exc)
            # VISA failures often leave a stale handle; close it and let the user rescan.
            text = str(exc).lower()
            if any(word in text for word in ("timeout", "connection", "device", "resource")):
                try:
                    self.connection.disconnect()
                except Exception:
                    pass
                self.connection_changed.emit(False, "", "")
        finally:
            self.busy = False

    @QtCore.Slot()
    def shutdown(self) -> None:
        if self.poll_timer:
            self.poll_timer.stop()
        if self.connection:
            try:
                self.connection.disconnect()
            except Exception:
                traceback.print_exc()
