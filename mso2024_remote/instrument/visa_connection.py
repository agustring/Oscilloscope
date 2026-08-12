from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Any


class VisaUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class VisaResourceInfo:
    resource: str
    identity: str = ""
    error: str = ""

    @property
    def is_mso2024(self) -> bool:
        text = self.identity.upper()
        return "TEKTRONIX" in text and "MSO2024" in text


def _pyvisa():
    try:
        import pyvisa
    except ImportError as exc:  # pragma: no cover - depends on local VISA install
        raise VisaUnavailableError(
            "PyVISA is not installed. Run 'python -m pip install -r requirements.txt'."
        ) from exc
    return pyvisa


class VisaConnection:
    """Thread-confined VISA resource manager and active instrument session."""

    def __init__(self, timeout_ms: int = 5000, backend: str | None = None):
        self.timeout_ms = timeout_ms
        self.backend = backend
        self.resource_manager: Any | None = None
        self.resource: Any | None = None
        self.resource_name = ""
        self.identity = ""
        self._owner_thread: int | None = None

    def _assert_thread(self) -> None:
        current = threading.get_ident()
        if self._owner_thread is None:
            self._owner_thread = current
        elif self._owner_thread != current:
            raise RuntimeError("VISA session accessed from a thread other than its owner")

    def _manager(self):
        self._assert_thread()
        if self.resource_manager is None:
            pyvisa = _pyvisa()
            try:
                # No explicit backend lets PyVISA prefer an installed IVI VISA
                # (NI-VISA/TekVISA) and fall back to pyvisa-py when available.
                self.resource_manager = (
                    pyvisa.ResourceManager(self.backend)
                    if self.backend
                    else pyvisa.ResourceManager()
                )
            except ValueError as exc:
                raise VisaUnavailableError(
                    "No VISA backend is available. Install NI-VISA or TekVISA, "
                    "or install the Python fallback with "
                    "'python -m pip install \"pyvisa-py[usb]\"'."
                ) from exc
        return self.resource_manager

    def discover(self) -> list[VisaResourceInfo]:
        """Enumerate resources and identify them using the IEEE 488.2 *IDN? query."""
        manager = self._manager()
        found: list[VisaResourceInfo] = []
        for name in manager.list_resources():
            probe = None
            try:
                probe = manager.open_resource(name)
                probe.timeout = min(self.timeout_ms, 1800)
                probe.write_termination = "\n"
                probe.read_termination = "\n"
                identity = str(probe.query("*IDN?")).strip()  # SCPI: *IDN?
                found.append(VisaResourceInfo(name, identity=identity))
            except Exception as exc:
                found.append(VisaResourceInfo(name, error=str(exc)))
            finally:
                if probe is not None:
                    try:
                        probe.close()
                    except Exception:
                        pass
        return sorted(found, key=lambda item: (not item.is_mso2024, item.resource))

    def connect(self, resource_name: str) -> str:
        self._assert_thread()
        self.disconnect()
        resource = self._manager().open_resource(resource_name)
        try:
            resource.timeout = self.timeout_ms
            resource.write_termination = "\n"
            resource.read_termination = "\n"
            identity = str(resource.query("*IDN?")).strip()  # SCPI: *IDN?
            if "TEKTRONIX" not in identity.upper() or "MSO2024" not in identity.upper():
                raise RuntimeError(f"Resource is not a Tektronix MSO2024: {identity}")
            resource.write("HEADER OFF")  # SCPI: HEADer OFF
            self.resource = resource
            self.resource_name = resource_name
            self.identity = identity
            return identity
        except Exception:
            resource.close()
            raise

    def disconnect(self) -> None:
        self._assert_thread()
        if self.resource is not None:
            try:
                self.resource.close()
            finally:
                self.resource = None
                self.resource_name = ""
                self.identity = ""

    def set_timeout(self, timeout_ms: int) -> None:
        self.timeout_ms = int(timeout_ms)
        if self.resource is not None:
            self.resource.timeout = self.timeout_ms

    @property
    def connected(self) -> bool:
        return self.resource is not None
