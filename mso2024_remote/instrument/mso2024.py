from __future__ import annotations

from dataclasses import asdict
import math
import re
from typing import Any

from .visa_connection import VisaConnection
from .waveform import Waveform, WaveformPreamble, parse_waveform


MEASUREMENT_TYPES = {
    "Amplitude": "AMPLITUDE",
    "Area": "AREA",
    "Burst Width": "BURST",
    "Cycle Area": "CAREA",
    "Cycle Mean": "CMEAN",
    "Cycle RMS": "CRMS",
    "Delay": "DELAY",
    "Fall Time": "FALL",
    "Frequency": "FREQUENCY",
    "High": "HIGH",
    "Low": "LOW",
    "Maximum": "MAXIMUM",
    "Mean": "MEAN",
    "Minimum": "MINIMUM",
    "Negative Duty": "NDUTY",
    "Falling Edge Count": "NEDGECOUNT",
    "Negative Overshoot": "NOVERSHOOT",
    "Negative Pulse Count": "NPULSECOUNT",
    "Negative Width": "NWIDTH",
    "Positive Duty": "PDUTY",
    "Rising Edge Count": "PEDGECOUNT",
    "Period": "PERIOD",
    "Phase": "PHASE",
    "Peak-to-Peak": "PK2PK",
    "Positive Overshoot": "POVERSHOOT",
    "Positive Pulse Count": "PPULSECOUNT",
    "Positive Width": "PWIDTH",
    "Rise Time": "RISE",
    "RMS": "RMS",
}

TRIGGER_KINDS = {
    "Edge": ("EDGE", None),
    "Pulse Width": ("PULSE", "WIDTH"),
    "Runt": ("PULSE", "RUNT"),
    "Rise/Fall Time": ("PULSE", "TRANSITION"),
    "Logic": ("LOGIC", "LOGIC"),
    "Setup/Hold": ("LOGIC", "SETHOLD"),
    "Video": ("VIDEO", None),
    "Serial Bus (option)": ("BUS", None),
}

SEARCH_KINDS = {
    "Edge": "EDGE",
    "Pulse Width": "PULSEWIDTH",
    "Runt": "RUNT",
    "Logic": "LOGIC",
    "Setup/Hold": "SETHOLD",
    "Rise/Fall Time": "TRANSITION",
    "Serial Bus (option)": "BUS",
}


def _strip(value: str) -> str:
    value = value.strip()
    if " " in value and value.startswith(":"):
        value = value.split(" ", 1)[1]
    return value.strip().strip('"')


def _float(value: str) -> float:
    return float(_strip(value))


def _bool(value: str) -> bool:
    return _strip(value).upper() not in {"0", "OFF", "FALSE", "STOP"}


def _quote(text: str, limit: int = 30) -> str:
    clean = text.replace('"', "'").replace("\r", " ").replace("\n", " ")[:limit]
    return f'"{clean}"'


class TektronixMSO2024:
    """Typed SCPI façade for commands documented in Tektronix 077-0097-01."""

    CHANNELS = (1, 2, 3, 4)
    RECORD_LENGTHS = (100_000, 1_000_000)
    AVERAGE_COUNTS = tuple(2**power for power in range(1, 10))

    def __init__(self, connection: VisaConnection):
        self.connection = connection
        self.last_command = ""
        self.last_response = ""

    @property
    def resource(self):
        resource = self.connection.resource
        if resource is None:
            raise RuntimeError("Oscilloscope is not connected")
        return resource

    def write(self, command: str) -> None:
        self.last_command = command
        self.resource.write(command)
        self.last_response = ""

    def query(self, command: str) -> str:
        self.last_command = command
        response = str(self.resource.query(command)).strip()
        self.last_response = response
        return response

    def query_raw(self, command: str) -> bytes:
        self.last_command = command
        # read_termination must be disabled so an arbitrary 0x0A sample cannot end CURVE?.
        termination = self.resource.read_termination
        try:
            self.resource.read_termination = None
            self.resource.write(command)
            response = bytes(self.resource.read_raw())
            self.last_response = f"<{len(response)} binary bytes>"
            return response
        finally:
            self.resource.read_termination = termination

    @staticmethod
    def _channel(channel: int) -> int:
        if int(channel) not in TektronixMSO2024.CHANNELS:
            raise ValueError("Channel must be 1, 2, 3, or 4")
        return int(channel)

    def set_channel_enabled(self, channel: int, enabled: bool) -> None:
        channel = self._channel(channel)
        self.write(f"SELECT:CH{channel} {'ON' if enabled else 'OFF'}")  # SCPI: SELect:CH<x>

    def channel_enabled(self, channel: int) -> bool:
        return _bool(self.query(f"SELECT:CH{self._channel(channel)}?"))

    def set_vertical_scale(self, channel: int, volts_per_div: float) -> None:
        channel = self._channel(channel)
        if not math.isfinite(volts_per_div) or volts_per_div <= 0:
            raise ValueError("Vertical scale must be a positive finite value")
        self.write(f"CH{channel}:SCALE {volts_per_div:.12g}")  # SCPI: CH<x>:SCAle

    def vertical_scale(self, channel: int) -> float:
        return _float(self.query(f"CH{self._channel(channel)}:SCALE?"))

    def set_vertical_position(self, channel: int, divisions: float) -> None:
        channel = self._channel(channel)
        if not -4.0 <= divisions <= 4.0:
            raise ValueError("Vertical position must be between -4 and +4 divisions")
        self.write(f"CH{channel}:POSITION {divisions:.6g}")  # SCPI: CH<x>:POSition

    def vertical_position(self, channel: int) -> float:
        return _float(self.query(f"CH{self._channel(channel)}:POSITION?"))

    def set_coupling(self, channel: int, coupling: str) -> None:
        coupling = coupling.upper()
        if coupling not in {"AC", "DC", "GND"}:
            raise ValueError("Coupling must be AC, DC, or GND")
        self.write(f"CH{self._channel(channel)}:COUPLING {coupling}")  # SCPI: CH<x>:COUPling

    def set_probe_attenuation(self, channel: int, attenuation: float) -> None:
        if not math.isfinite(attenuation) or attenuation <= 0:
            raise ValueError("Probe attenuation must be positive")
        # The programmer manual defines probe GAIN as output/input: a 10x probe is 0.1.
        self.write(f"CH{self._channel(channel)}:PROBE:GAIN {1.0 / attenuation:.12g}")

    def probe_attenuation(self, channel: int) -> float:
        gain = _float(self.query(f"CH{self._channel(channel)}:PROBE:GAIN?"))
        return 1.0 / gain if gain else math.inf

    def set_bandwidth(self, channel: int, bandwidth: str) -> None:
        value = {"20 MHZ": "TWENTY", "FULL": "FULL"}.get(bandwidth.upper())
        if value is None:
            raise ValueError("Bandwidth must be '20 MHz' or 'Full'")
        self.write(f"CH{self._channel(channel)}:BANDWIDTH {value}")  # SCPI: CH<x>:BANdwidth

    def set_invert(self, channel: int, enabled: bool) -> None:
        self.write(f"CH{self._channel(channel)}:INVERT {'ON' if enabled else 'OFF'}")  # SCPI: CH<x>:INVert

    def set_channel_label(self, channel: int, label: str) -> None:
        self.write(f"CH{self._channel(channel)}:LABEL {_quote(label)}")  # SCPI: CH<x>:LABel

    def channel_state(self, channel: int) -> dict[str, Any]:
        channel = self._channel(channel)
        return {
            "enabled": self.channel_enabled(channel),
            "scale": self.vertical_scale(channel),
            "position": self.vertical_position(channel),
            "coupling": _strip(self.query(f"CH{channel}:COUPLING?")).upper(),
            "attenuation": self.probe_attenuation(channel),
            "bandwidth": _strip(self.query(f"CH{channel}:BANDWIDTH?")).upper(),
            "invert": _bool(self.query(f"CH{channel}:INVERT?")),
            "label": _strip(self.query(f"CH{channel}:LABEL?")),
        }

    def set_time_scale(self, seconds_per_div: float) -> None:
        if not 2e-9 <= seconds_per_div <= 100.0:
            raise ValueError("MSO2024 time scale must be between 2 ns/div and 100 s/div")
        self.write(f"HORIZONTAL:SCALE {seconds_per_div:.12g}")  # SCPI: HORizontal:SCAle

    def time_scale(self) -> float:
        return _float(self.query("HORIZONTAL:SCALE?"))

    def set_horizontal_position(self, percent: float) -> None:
        self.write("HORIZONTAL:DELAY:MODE OFF")  # SCPI: HORizontal:DELay:MODe
        self.write(f"HORIZONTAL:POSITION {max(0.0, min(100.0, percent)):.8g}")  # SCPI: HORizontal:POSition

    def set_delay(self, seconds: float) -> None:
        self.write("HORIZONTAL:DELAY:MODE ON")  # SCPI: HORizontal:DELay:MODe
        self.write(f"HORIZONTAL:DELAY:TIME {seconds:.12g}")  # SCPI: HORizontal:DELay:TIMe

    def set_record_length(self, points: int) -> None:
        if int(points) not in self.RECORD_LENGTHS:
            raise ValueError("MSO2024 record length must be 100000 or 1000000")
        self.write(f"HORIZONTAL:RECORDLENGTH {int(points)}")  # SCPI: HORizontal:RECOrdlength

    def horizontal_state(self) -> dict[str, Any]:
        delay_mode = _bool(self.query("HORIZONTAL:DELAY:MODE?"))
        return {
            "scale": self.time_scale(),
            "position": _float(self.query("HORIZONTAL:POSITION?")),
            "delay_mode": delay_mode,
            "delay": _float(self.query("HORIZONTAL:DELAY:TIME?")),
            "record_length": int(_float(self.query("HORIZONTAL:RECORDLENGTH?"))),
        }

    def run(self) -> None:
        self.write("ACQUIRE:STOPAFTER RUNSTOP")  # SCPI: ACQuire:STOPAfter
        self.write("ACQUIRE:STATE RUN")  # SCPI: ACQuire:STATE

    def stop(self) -> None:
        self.write("ACQUIRE:STATE STOP")  # SCPI: ACQuire:STATE

    def single(self) -> None:
        self.write("ACQUIRE:STOPAFTER SEQUENCE")  # SCPI: ACQuire:STOPAfter
        self.write("ACQUIRE:STATE RUN")  # SCPI: ACQuire:STATE

    def autoset(self) -> None:
        self.write("AUTOSET EXECUTE")  # SCPI: AUTOSet EXECute

    def force_trigger(self) -> None:
        self.write("TRIGGER FORCE")  # SCPI: TRIGger FORCe

    def open_test_menu(self) -> None:
        self.write("FPANEL:PRESS TEST")  # SCPI: FPAnel:PRESS TESt

    def set_zoom_enabled(self, enabled: bool) -> None:
        self.write(f"ZOOM:MODE {'ON' if enabled else 'OFF'}")  # SCPI: ZOOm:MODe

    def set_zoom_scale(self, seconds: float) -> None:
        if not 1e-3 <= seconds <= 5.0:
            raise ValueError("MSO2024 zoom scale must be between 1 ms and 5 s")
        self.write(f"ZOOM:ZOOM1:SCALE {seconds:.12g}")  # SCPI: ZOOm:ZOOM1:SCAle

    def set_zoom_position(self, percent: float) -> None:
        if not 0.0 <= percent <= 100.0:
            raise ValueError("Zoom position must be between 0 and 100 percent")
        self.write(f"ZOOM:ZOOM1:POSITION {percent:.8g}")  # SCPI: ZOOm:ZOOM1:POSition

    def zoom_state(self) -> dict[str, Any]:
        return {
            "enabled": _bool(self.query("ZOOM:MODE?")),
            "scale": _float(self.query("ZOOM:ZOOM1:SCALE?")),
            "position": _float(self.query("ZOOM:ZOOM1:POSITION?")),
        }

    def move_to_mark(self, direction: str) -> None:
        direction = direction.upper()
        if direction not in {"NEXT", "PREVIOUS"}:
            raise ValueError("Mark direction must be NEXT or PREVIOUS")
        self.write(f"MARK {'NEXT' if direction == 'NEXT' else 'PREVIOUS'}")  # SCPI: MARK

    def create_mark(self, source: str) -> None:
        source = source.upper()
        if source not in {f"CH{x}" for x in self.CHANNELS} | {"MATH", "REF1", "REF2", "COLUMN", "DIGITAL"}:
            raise ValueError("Unsupported mark source")
        self.write(f"MARK:CREATE {source}")  # SCPI: MARK:CREATE

    def toggle_mark(self) -> None:
        self.write("FPANEL:PRESS MARK")  # SCPI: FPAnel:PRESS MARk (Set/Clear Mark)

    def toggle_wave_inspector_playback(self) -> None:
        self.write("FPANEL:PRESS PAUSE")  # SCPI: FPAnel:PRESS PAUse (Wave Inspector play/pause)

    def set_search_enabled(self, enabled: bool) -> None:
        self.write(f"SEARCH:SEARCH1:STATE {'ON' if enabled else 'OFF'}")  # SCPI: SEARCH:SEARCH<x>:STATE

    def set_search_kind(self, label: str) -> None:
        if label not in SEARCH_KINDS:
            raise ValueError(f"Unknown search kind: {label}")
        self.write(f"SEARCH:SEARCH1:TRIGGER:A:TYPE {SEARCH_KINDS[label]}")  # SCPI: SEARCH:SEARCH<x>:TRIGger:A:TYPe

    def configure_edge_search(self, source: str, slope: str, level: float) -> None:
        source, slope = source.upper(), slope.upper()
        if source not in {f"CH{x}" for x in self.CHANNELS} | {"MATH"}:
            raise ValueError("Edge search source must be CH1 through CH4 or MATH")
        if slope not in {"RISE", "FALL"}:
            raise ValueError("Edge search slope must be RISE or FALL")
        prefix = "SEARCH:SEARCH1:TRIGGER:A"
        self.write(f"{prefix}:EDGE:SOURCE {source}")
        self.write(f"{prefix}:EDGE:SLOPE {slope}")
        self.write(f"{prefix}:LEVEL {level:.12g}")

    def configure_pulse_search(
        self, kind: str, source: str, polarity: str, condition: str, seconds: float
    ) -> None:
        branch = {"Pulse Width": "PULSEWIDTH", "Runt": "RUNT", "Rise/Fall Time": "TRANSITION"}.get(kind)
        if branch is None:
            raise ValueError("Not a pulse-family search kind")
        source, polarity, condition = source.upper(), polarity.upper(), condition.upper()
        if source not in {f"CH{x}" for x in self.CHANNELS} | {"MATH"}:
            raise ValueError("Pulse search source must be CH1 through CH4 or MATH")
        allowed_polarities = {"POSITIVE", "NEGATIVE"} if kind == "Pulse Width" else {"POSITIVE", "NEGATIVE", "EITHER"}
        if polarity not in allowed_polarities:
            raise ValueError("Unsupported search polarity")
        allowed_conditions = {"SLOWER", "FASTER", "EQUAL", "UNEQUAL"} if kind == "Rise/Fall Time" else {"LESSTHAN", "MORETHAN", "EQUAL", "UNEQUAL"}
        if kind == "Runt": allowed_conditions.add("OCCURS")
        if condition not in allowed_conditions:
            raise ValueError("Unsupported pulse search condition")
        prefix = f"SEARCH:SEARCH1:TRIGGER:A:{branch}"
        self.write(f"{prefix}:SOURCE {source}")
        self.write(f"{prefix}:POLARITY {polarity}")
        self.write(f"{prefix}:WHEN {condition}")
        leaf = "DELTATIME" if kind == "Rise/Fall Time" else "WIDTH"
        self.write(f"{prefix}:{leaf} {seconds:.12g}")

    def configure_logic_search(
        self, ch1: str, ch2: str, ch3: str, ch4: str, when: str, seconds: float
    ) -> None:
        values = [ch1.upper(), ch2.upper(), ch3.upper(), ch4.upper()]
        if any(value not in {"HIGH", "LOW", "X"} for value in values):
            raise ValueError("Logic search inputs must be HIGH, LOW, or X")
        when = when.upper()
        if when not in {"TRUE", "FALSE", "LESSTHAN", "MORETHAN"}:
            raise ValueError("Unsupported logic search condition")
        prefix = "SEARCH:SEARCH1:TRIGGER:A:LOGIC:PATTERN"
        for channel, value in enumerate(values, 1):
            self.write(f"{prefix}:INPUT:CH{channel} {value}")
        self.write(f"{prefix}:WHEN {when}")
        if when == "LESSTHAN": self.write(f"{prefix}:WHEN:LESSLIMIT {seconds:.12g}")
        elif when == "MORETHAN": self.write(f"{prefix}:WHEN:MORELIMIT {seconds:.12g}")

    def configure_setup_hold_search(
        self,
        clock_source: str,
        clock_edge: str,
        clock_threshold: float,
        data_source: str,
        data_threshold: float,
        setup_time: float,
        hold_time: float,
    ) -> None:
        allowed_clock = {f"CH{x}" for x in self.CHANNELS} | {"MATH", "REF"}
        allowed_data = allowed_clock | {f"D{x}" for x in range(16)}
        clock_source, clock_edge, data_source = clock_source.upper(), clock_edge.upper(), data_source.upper()
        if clock_source not in allowed_clock or data_source not in allowed_data or clock_source == data_source:
            raise ValueError("Setup/Hold search sources must be valid and distinct")
        if clock_edge not in {"RISE", "FALL"}:
            raise ValueError("Setup/Hold search clock edge must be RISE or FALL")
        prefix = "SEARCH:SEARCH1:TRIGGER:A:SETHOLD"
        self.write(f"{prefix}:CLOCK:SOURCE {clock_source}")
        self.write(f"{prefix}:CLOCK:EDGE {clock_edge}")
        self.write(f"{prefix}:CLOCK:THRESHOLD {clock_threshold:.12g}")
        self.write(f"{prefix}:DATA:SOURCE {data_source}")
        self.write(f"{prefix}:DATA:THRESHOLD {data_threshold:.12g}")
        self.write(f"{prefix}:SETTIME {setup_time:.12g}")
        self.write(f"{prefix}:HOLDTIME {hold_time:.12g}")

    def set_search_bus_source(self, bus: int) -> None:
        if bus not in {1, 2}:
            raise ValueError("Search bus source must be B1 or B2")
        self.write(f"SEARCH:SEARCH1:TRIGGER:A:BUS:SOURCE B{bus}")

    def copy_search_settings(self, search_to_trigger: bool) -> None:
        direction = "SEARCHTOTRIGGER" if search_to_trigger else "TRIGGERTOSEARCH"
        self.write(f"SEARCH:SEARCH1:COPY {direction}")  # SCPI: SEARCH:SEARCH<x>:COPy

    def set_language(self, language: str) -> None:
        allowed = {"ENGLISH", "FRENCH", "GERMAN", "ITALIAN", "SPANISH", "PORTUGUESE", "JAPANESE", "KOREAN", "RUSSIAN", "SIMPLIFIEDCHINESE", "TRADITIONALCHINESE"}
        language = language.upper().replace(" ", "")
        if language not in allowed:
            raise ValueError("Unsupported MSO2024 language")
        self.write(f"LANGUAGE {language}")  # SCPI: LANGuage

    def configure_math(self, expression: str) -> None:
        clean = expression.upper().replace(" ", "")
        if clean.startswith("FFT(") and clean.endswith(")"):
            source = clean[4:-1]
            if source not in {f"CH{x}" for x in self.CHANNELS} | {"REF1", "REF2"}:
                raise ValueError("Unsupported FFT source")
            self.write("MATH1:TYPE FFT")  # SCPI: MATH[1]:TYPe
        elif not re.fullmatch(r"(?:CH[1-4]|REF[12])[+\-*](?:CH[1-4]|REF[12])", clean):
            raise ValueError("Unsupported dual waveform math expression")
        else:
            self.write("MATH1:TYPE DUAL")
        self.write(f'MATH1:DEFINE "{clean}"')  # SCPI: MATH[1]:DEFine
        self.write("SELECT:MATH ON")  # SCPI: SELect:MATH

    def set_reference_enabled(self, reference: int, enabled: bool) -> None:
        if reference not in {1, 2}:
            raise ValueError("Reference must be 1 or 2")
        self.write(f"SELECT:REF{reference} {'ON' if enabled else 'OFF'}")  # SCPI: SELect:REF<x>

    def save_setup(self, slot: int) -> None:
        if slot not in range(1, 11):
            raise ValueError("Setup slot must be 1 through 10")
        self.write(f"SAVE:SETUP {slot}")  # SCPI: SAVe:SETUp

    def recall_setup(self, slot: int) -> None:
        if slot not in range(1, 11):
            raise ValueError("Setup slot must be 1 through 10")
        self.write(f"RECALL:SETUP {slot}")  # SCPI: RECAll:SETUp

    def default_setup(self) -> None:
        self.write("RECALL:SETUP FACTORY")  # SCPI: RECAll:SETUp FACtory

    def set_acquisition_mode(self, mode: str, averages: int | None = None) -> None:
        mode = mode.upper()
        if mode not in {"SAMPLE", "AVERAGE"}:
            raise ValueError("MSO2024 programmer manual documents SAMPLE and AVERAGE modes")
        self.write(f"ACQUIRE:MODE {mode}")  # SCPI: ACQuire:MODe
        if mode == "AVERAGE" and averages is not None:
            if averages not in self.AVERAGE_COUNTS:
                raise ValueError("Average count must be a power of two from 2 through 512")
            self.write(f"ACQUIRE:NUMAVG {averages}")  # SCPI: ACQuire:NUMAVg

    def acquisition_state(self) -> dict[str, Any]:
        return {
            "running": _bool(self.query("ACQUIRE:STATE?")),
            "mode": _strip(self.query("ACQUIRE:MODE?")).upper(),
            "averages": int(_float(self.query("ACQUIRE:NUMAVG?"))),
            "stop_after": _strip(self.query("ACQUIRE:STOPAFTER?")).upper(),
        }

    def set_trigger_kind(self, label: str) -> None:
        if label not in TRIGGER_KINDS:
            raise ValueError(f"Unknown trigger kind: {label}")
        trigger_type, trigger_class = TRIGGER_KINDS[label]
        self.write(f"TRIGGER:A:TYPE {trigger_type}")  # SCPI: TRIGger:A:TYPe
        if trigger_type == "PULSE":
            self.write(f"TRIGGER:A:PULSE:CLASS {trigger_class}")  # SCPI: TRIGger:A:PULse:CLAss
        elif trigger_type == "LOGIC":
            self.write(f"TRIGGER:A:LOGIC:CLASS {trigger_class}")  # SCPI: TRIGger:A:LOGIc:CLAss

    def trigger_kind(self) -> str:
        trigger_type = _strip(self.query("TRIGGER:A:TYPE?")).upper()
        if trigger_type == "PULSE":
            trigger_class = _strip(self.query("TRIGGER:A:PULSE:CLASS?")).upper()
            return {"WIDTH": "Pulse Width", "RUNT": "Runt", "TRANSITION": "Rise/Fall Time"}.get(trigger_class, "Pulse Width")
        if trigger_type == "LOGIC":
            trigger_class = _strip(self.query("TRIGGER:A:LOGIC:CLASS?")).upper()
            return "Setup/Hold" if trigger_class == "SETHOLD" else "Logic"
        return {"EDGE": "Edge", "VIDEO": "Video", "BUS": "Serial Bus (option)"}.get(trigger_type, "Edge")

    def trigger_system_state(self) -> str:
        return _strip(self.query("TRIGGER:STATE?")).upper()  # SCPI: TRIGger:STATE?

    def set_edge_source(self, source: str) -> None:
        allowed = {f"CH{x}" for x in self.CHANNELS} | {f"D{x}" for x in range(16)} | {"EXT", "LINE", "AUX"}
        source = source.upper()
        if source not in allowed:
            raise ValueError("Unsupported edge trigger source")
        self.write(f"TRIGGER:A:EDGE:SOURCE {source}")  # SCPI: TRIGger:A:EDGE:SOUrce

    def set_trigger_level(self, channel: int, volts: float) -> None:
        self.write(f"TRIGGER:A:LEVEL:CH{self._channel(channel)} {volts:.12g}")  # SCPI: TRIGger:A:LEVel:CH<x>

    def set_edge_slope(self, slope: str) -> None:
        slope = slope.upper()
        if slope not in {"RISE", "FALL"}:
            raise ValueError("MSO2024 edge slope must be RISE or FALL")
        self.write(f"TRIGGER:A:EDGE:SLOPE {slope}")  # SCPI: TRIGger:A:EDGE:SLOpe

    def set_edge_coupling(self, coupling: str) -> None:
        coupling = coupling.upper()
        if coupling not in {"DC", "HFREJ", "LFREJ", "NOISEREJ"}:
            raise ValueError("Unsupported edge trigger coupling")
        self.write(f"TRIGGER:A:EDGE:COUPLING {coupling}")  # SCPI: TRIGger:A:EDGE:COUPling

    def set_trigger_mode(self, mode: str) -> None:
        mode = mode.upper()
        if mode not in {"AUTO", "NORMAL"}:
            raise ValueError("Trigger mode must be AUTO or NORMAL")
        self.write(f"TRIGGER:A:MODE {mode}")  # SCPI: TRIGger:A:MODe

    def set_trigger_holdoff(self, seconds: float) -> None:
        if not 20e-9 <= seconds <= 8.0:
            raise ValueError("Trigger holdoff must be between 20 ns and 8 s")
        self.write(f"TRIGGER:A:HOLDOFF:TIME {seconds:.12g}")  # SCPI: TRIGger:A:HOLDoff:TIMe

    def set_pulse_source(self, kind: str, source: str) -> None:
        branch = {"Pulse Width": "PULSEWIDTH", "Runt": "RUNT", "Rise/Fall Time": "TRANSITION"}.get(kind)
        if branch is None or source.upper() not in {f"CH{x}" for x in self.CHANNELS}:
            raise ValueError("This trigger source control supports CH1 through CH4")
        self.write(f"TRIGGER:A:{branch}:SOURCE {source.upper()}")  # SCPI: TRIGger:A:{PULSEWidth|RUNT|TRANsition}:SOUrce

    def set_pulse_parameter(self, kind: str, polarity: str, condition: str, seconds: float) -> None:
        branch = {"Pulse Width": "PULSEWIDTH", "Runt": "RUNT", "Rise/Fall Time": "TRANSITION"}.get(kind)
        if branch is None:
            raise ValueError("Not a pulse trigger kind")
        polarity = polarity.upper()
        condition = condition.upper()
        allowed_polarities = {"POSITIVE", "NEGATIVE", "EITHER"} if kind in {"Runt", "Rise/Fall Time"} else {"POSITIVE", "NEGATIVE"}
        if polarity not in allowed_polarities:
            raise ValueError(f"Unsupported {kind} polarity")
        allowed = {"SLOWER", "FASTER", "EQUAL", "UNEQUAL"} if kind == "Rise/Fall Time" else {"LESSTHAN", "MORETHAN", "EQUAL", "UNEQUAL"}
        if kind == "Runt":
            allowed.add("OCCURS")
        if condition not in allowed:
            raise ValueError("Unsupported pulse trigger condition")
        self.write(f"TRIGGER:A:{branch}:POLARITY {polarity}")  # SCPI: TRIGger:A:{PULSEWidth|RUNT|TRANsition}:POLarity
        self.write(f"TRIGGER:A:{branch}:WHEN {condition}")  # SCPI: TRIGger:A:{PULSEWidth|RUNT|TRANsition}:WHEn
        leaf = "DELTATIME" if kind == "Rise/Fall Time" else "WIDTH"
        self.write(f"TRIGGER:A:{branch}:{leaf} {seconds:.12g}")  # SCPI: ...:WIDth / ...:DELTatime

    def configure_logic_trigger(
        self,
        ch1: str,
        ch2: str,
        ch3: str,
        ch4: str,
        function: str,
        when: str,
        delta_time: float,
        clock_source: str = "NONE",
        clock_edge: str = "RISE",
        digital_inputs: tuple[str, ...] | list[str] | None = None,
        threshold_source: str | None = None,
        threshold: float = 1.4,
    ) -> None:
        values = [ch1.upper(), ch2.upper(), ch3.upper(), ch4.upper()]
        if any(value not in {"HIGH", "LOW", "X"} for value in values):
            raise ValueError("Logic inputs must be HIGH, LOW, or X")
        if function.upper() not in {"AND", "NAND"}:
            raise ValueError("Logic function must be AND or NAND")
        if when.upper() not in {"TRUE", "FALSE", "LESSTHAN", "MORETHAN", "EQUAL", "UNEQUAL"}:
            raise ValueError("Unsupported logic pattern condition")
        if not 39.6e-9 <= delta_time <= 10.0:
            raise ValueError("Logic delta time must be between 39.6 ns and 10 s")
        allowed_sources = {"NONE"} | {f"CH{x}" for x in self.CHANNELS} | {f"D{x}" for x in range(16)}
        if clock_source.upper() not in allowed_sources or clock_edge.upper() not in {"RISE", "FALL", "EITHER"}:
            raise ValueError("Unsupported logic clock source or edge")
        digital_values = None
        if digital_inputs is not None:
            digital_values = [value.upper() for value in digital_inputs]
            if len(digital_values) != 4 or any(value not in {"HIGH", "LOW", "X"} for value in digital_values):
                raise ValueError("Digital logic inputs must contain four HIGH, LOW, or X values")
        if threshold_source is not None:
            threshold_source = threshold_source.upper()
            if threshold_source not in ({f"CH{x}" for x in self.CHANNELS} | {f"D{x}" for x in range(16)}):
                raise ValueError("Logic threshold source must be CH1-CH4 or D0-D15")
        self.write(f"TRIGGER:A:LOGIC:FUNCTION {function.upper()}")  # SCPI: TRIGger:A:LOGIc:FUNCtion
        for channel, value in enumerate(values, 1):
            self.write(f"TRIGGER:A:LOGIC:INPUT:CH{channel} {value}")  # SCPI: TRIGger:A:LOGIc:INPut:CH<x>
        if digital_values is not None:
            for channel, value in enumerate(digital_values):
                self.write(f"TRIGGER:A:LOGIC:INPUT:D{channel} {value}")  # SCPI: TRIGger:A:LOGIc:INPut:D<x>
        if threshold_source is not None:
            self.write(f"TRIGGER:A:LOGIC:THRESHOLD:{threshold_source} {threshold:.12g}")  # SCPI: TRIGger:A:LOGIc:THReshold:{CH<x>|D<x>}
        self.write(f"TRIGGER:A:LOGIC:INPUT:CLOCK:SOURCE {clock_source.upper()}")  # SCPI: TRIGger:A:LOGIc:INPut:CLOCk:SOUrce
        if clock_source.upper() != "NONE":
            self.write(f"TRIGGER:A:LOGIC:INPUT:CLOCK:EDGE {clock_edge.upper()}")  # SCPI: TRIGger:A:LOGIc:INPut:CLOCk:EDGE
        self.write(f"TRIGGER:A:LOGIC:PATTERN:WHEN {when.upper()}")  # SCPI: TRIGger:A:LOGIc:PATtern:WHEn
        if when.upper() not in {"TRUE", "FALSE"}:
            self.write(f"TRIGGER:A:LOGIC:PATTERN:DELTATIME {delta_time:.12g}")  # SCPI: TRIGger:A:LOGIc:PATtern:DELTatime

    def configure_setup_hold_trigger(
        self,
        clock_source: str,
        clock_edge: str,
        clock_threshold: float,
        data_source: str,
        data_threshold: float,
        setup_time: float,
        hold_time: float,
    ) -> None:
        allowed = {f"CH{x}" for x in self.CHANNELS} | {f"D{x}" for x in range(16)}
        clock_source, data_source, clock_edge = clock_source.upper(), data_source.upper(), clock_edge.upper()
        if clock_source not in allowed or data_source not in allowed:
            raise ValueError("Setup/Hold sources must be CH1–CH4 or D0–D15")
        if clock_source == data_source:
            raise ValueError("Setup/Hold clock and data sources must differ")
        if clock_edge not in {"RISE", "FALL"}:
            raise ValueError("Setup/Hold clock edge must be RISE or FALL")
        self.write(f"TRIGGER:A:SETHOLD:CLOCK:SOURCE {clock_source}")  # SCPI: TRIGger:A:SETHold:CLOCk:SOUrce
        self.write(f"TRIGGER:A:SETHOLD:CLOCK:EDGE {clock_edge}")  # SCPI: TRIGger:A:SETHold:CLOCk:EDGE
        self.write(f"TRIGGER:A:SETHOLD:CLOCK:THRESHOLD {clock_threshold:.12g}")  # SCPI: TRIGger:A:SETHold:CLOCk:THReshold
        self.write(f"TRIGGER:A:SETHOLD:DATA:SOURCE {data_source}")  # SCPI: TRIGger:A:SETHold:DATa:SOUrce
        self.write(f"TRIGGER:A:SETHOLD:DATA:THRESHOLD {data_threshold:.12g}")  # SCPI: TRIGger:A:SETHold:DATa:THReshold
        self.write(f"TRIGGER:A:SETHOLD:SETTIME {setup_time:.12g}")  # SCPI: TRIGger:A:SETHold:SETTime
        self.write(f"TRIGGER:A:SETHOLD:HOLDTIME {hold_time:.12g}")  # SCPI: TRIGger:A:SETHold:HOLDTime

    def set_video_trigger(self, source: str, polarity: str, standard: str) -> None:
        if source.upper() not in {f"CH{x}" for x in self.CHANNELS}:
            raise ValueError("Video trigger source must be CH1 through CH4")
        if polarity.upper() not in {"POSITIVE", "NEGATIVE"}:
            raise ValueError("Video polarity must be POSITIVE or NEGATIVE")
        if standard.upper() not in {"NTSC", "PAL", "SECAM"}:
            raise ValueError("Video standard must be NTSC, PAL, or SECAM")
        self.write(f"TRIGGER:A:VIDEO:SOURCE {source.upper()}")  # SCPI: TRIGger:A:VIDeo:SOUrce
        self.write(f"TRIGGER:A:VIDEO:POLARITY {polarity.upper()}")  # SCPI: TRIGger:A:VIDeo:POLarity
        self.write(f"TRIGGER:A:VIDEO:STANDARD {standard.upper()}")  # SCPI: TRIGger:A:VIDeo:STANdard

    def set_bus_type(self, bus: int, bus_type: str) -> None:
        if bus not in {1, 2}:
            raise ValueError("Bus number must be 1 or 2")
        code = {
            "Parallel": "PARALLEL",
            "I2C": "I2C",
            "SPI": "SPI",
            "CAN": "CAN",
            "LIN": "LIN",
            "RS-232": "RS232C",
        }.get(bus_type)
        if code is None:
            raise ValueError("Unsupported MSO2024 bus type")
        self.write(f"BUS:B{bus}:TYPE {code}")  # SCPI: BUS:B<x>:TYPE
        self.write(f"BUS:B{bus}:STATE ON")  # SCPI: BUS:B<x>:STATE

    def trigger_state(self) -> dict[str, Any]:
        kind = self.trigger_kind()
        state: dict[str, Any] = {
            "kind": kind,
            "status": self.trigger_system_state(),
            "mode": _strip(self.query("TRIGGER:A:MODE?")).upper(),
            "holdoff": _float(self.query("TRIGGER:A:HOLDOFF:TIME?")),
        }
        if kind == "Edge":
            source = _strip(self.query("TRIGGER:A:EDGE:SOURCE?")).upper()
            state.update(
                source=source,
                slope=_strip(self.query("TRIGGER:A:EDGE:SLOPE?")).upper(),
                coupling=_strip(self.query("TRIGGER:A:EDGE:COUPLING?")).upper(),
            )
            if re.fullmatch(r"CH[1-4]", source):
                state["level"] = _float(self.query(f"TRIGGER:A:LEVEL:{source}?"))
        return state

    def configure_measurement(
        self,
        slot: int,
        type_code: str,
        source: str,
        enabled: bool = True,
        source2: str | None = None,
    ) -> None:
        if slot not in range(1, 5):
            raise ValueError("MSO2024 supports measurement slots 1 through 4")
        if type_code.upper() not in MEASUREMENT_TYPES.values():
            raise ValueError("Unsupported MSO2024 measurement type")
        if source.upper() not in {f"CH{x}" for x in self.CHANNELS} | {"MATH1", "REF1", "REF2"}:
            raise ValueError("Unsupported measurement source")
        self.write(f"MEASUREMENT:MEAS{slot}:SOURCE1 {source.upper()}")  # SCPI: MEASUrement:MEAS<x>:SOURCE[1]
        if type_code.upper() in {"DELAY", "PHASE"}:
            if not source2 or source2.upper() not in {f"CH{x}" for x in self.CHANNELS} | {"MATH1", "REF1", "REF2"}:
                raise ValueError("Delay and Phase measurements require a valid second source")
            self.write(f"MEASUREMENT:MEAS{slot}:SOURCE2 {source2.upper()}")  # SCPI: MEASUrement:MEAS<x>:SOURCE2
        self.write(f"MEASUREMENT:MEAS{slot}:TYPE {type_code.upper()}")  # SCPI: MEASUrement:MEAS<x>:TYPe
        self.write(f"MEASUREMENT:MEAS{slot}:STATE {'ON' if enabled else 'OFF'}")  # SCPI: MEASUrement:MEAS<x>:STATE

    def disable_measurement(self, slot: int) -> None:
        if slot not in range(1, 5):
            raise ValueError("MSO2024 supports measurement slots 1 through 4")
        self.write(f"MEASUREMENT:MEAS{slot}:STATE OFF")

    def set_measurement_indicators(self, slot: int | None) -> None:
        if slot is not None and slot not in range(1, 5):
            raise ValueError("Measurement indicator slot must be 1 through 4")
        self.write(f"MEASUREMENT:INDICATORS:STATE {'OFF' if slot is None else f'MEAS{slot}'}")

    def set_measurement_gating(self, mode: str) -> None:
        mode = mode.upper()
        if mode not in {"OFF", "SCREEN", "CURSOR"}:
            raise ValueError("Measurement gating must be OFF, SCREEN, or CURSOR")
        self.write(f"MEASUREMENT:GATING {mode}")

    def set_measurement_method(self, method: str) -> None:
        method = method.upper()
        if method not in {"AUTO", "HISTOGRAM", "MINMAX"}:
            raise ValueError("Measurement method must be AUTO, HISTOGRAM, or MINMAX")
        self.write(f"MEASUREMENT:METHOD {method}")

    def measurement_state(self, slot: int) -> dict[str, Any]:
        enabled = _bool(self.query(f"MEASUREMENT:MEAS{slot}:STATE?"))
        result: dict[str, Any] = {"slot": slot, "enabled": enabled}
        if enabled:
            result.update(
                type=_strip(self.query(f"MEASUREMENT:MEAS{slot}:TYPE?")).upper(),
                source=_strip(self.query(f"MEASUREMENT:MEAS{slot}:SOURCE1?")).upper(),
                value=_float(self.query(f"MEASUREMENT:MEAS{slot}:VALUE?")),
                unit=_strip(self.query(f"MEASUREMENT:MEAS{slot}:UNITS?")),
            )
        return result

    def set_cursor_function(self, function: str) -> None:
        function = function.upper()
        if function not in {"OFF", "VBARS", "HBARS", "SCREEN", "WAVEFORM"}:
            raise ValueError("Unsupported cursor function")
        self.write(f"CURSOR:FUNCTION {function}")  # SCPI: CURSor:FUNCtion
        if function == "VBARS":
            self.write("CURSOR:VBARS:UNITS SECONDS")  # SCPI: CURSor:VBArs:UNIts
        elif function == "HBARS":
            self.write("CURSOR:HBARS:UNITS BASE")  # SCPI: CURSor:HBArs:UNIts

    def set_cursor_position(self, axis: str, cursor: int, value: float) -> None:
        if axis.upper() not in {"VBARS", "HBARS"} or cursor not in {1, 2}:
            raise ValueError("Cursor must be VBARS/HBARS and position 1/2")
        self.write(f"CURSOR:{axis.upper()}:POSITION{cursor} {value:.12g}")

    def set_cursor_mode(self, mode: str) -> None:
        mode = mode.upper()
        if mode not in {"TRACK", "INDEPENDENT"}:
            raise ValueError("Cursor mode must be TRACK or INDEPENDENT")
        self.write(f"CURSOR:MODE {mode}")  # SCPI: CURSor:MODe

    def cursor_state(self) -> dict[str, Any]:
        function = _strip(self.query("CURSOR:FUNCTION?")).upper()
        state: dict[str, Any] = {"function": function}
        if function in {"VBARS", "SCREEN", "WAVEFORM"}:
            state.update(
                x1=_float(self.query("CURSOR:VBARS:POSITION1?")),
                x2=_float(self.query("CURSOR:VBARS:POSITION2?")),
                dx=_float(self.query("CURSOR:VBARS:DELTA?")),
            )
        if function == "WAVEFORM":
            state.update(
                vdelta=_float(self.query("CURSOR:VBARS:VDELTA?")),
                mode=_strip(self.query("CURSOR:MODE?")).upper(),
            )
        if function in {"HBARS", "SCREEN"}:
            state.update(
                y1=_float(self.query("CURSOR:HBARS:POSITION1?")),
                y2=_float(self.query("CURSOR:HBARS:POSITION2?")),
                dy=_float(self.query("CURSOR:HBARS:DELTA?")),
            )
        return state

    def waveform(
        self,
        channel: int,
        max_points: int = 6250,
        full_resolution: bool = False,
        assume_enabled: bool = False,
    ) -> Waveform:
        channel = self._channel(channel)
        if not assume_enabled and not self.channel_enabled(channel):
            raise RuntimeError(f"CH{channel} is not displayed")
        # SCPI: DATa:SOUrce, RESOlution, ENCdg, WIDth, STARt.
        self.write(
            f"DATA:SOURCE CH{channel};:DATA:RESOLUTION {'FULL' if full_resolution else 'REDUCED'};"
            ":DATA:ENCDG SRIBINARY;:DATA:WIDTH 2;:DATA:START 1"
        )
        # Prefer ordinary Y-versus-time data. COMPOSITE_ENV contains interleaved
        # min/max pairs and must not be silently interpreted as regular samples.
        available = _strip(self.query("DATA:COMPOSITION:AVAILABLE?")).upper().replace(",", " ")
        composition = "SINGULAR_YT" if "SINGULAR_YT" in available else "COMPOSITE_YT"
        self.write(f"DATA:COMPOSITION {composition}")  # SCPI: DATa:COMPosition
        record_length = int(_float(self.query("WFMOUTPRE:RECORDLENGTH?")))
        stop = record_length if full_resolution else min(max_points, record_length)
        self.write(f"DATA:STOP {max(1, stop)}")  # SCPI: DATa:STOP
        # One concatenated query substantially reduces USB round trips while
        # preserving every scaling field from the official waveform preamble.
        preamble_response = self.query(
            "WFMOUTPRE:XINCR?;:WFMOUTPRE:XZERO?;:WFMOUTPRE:YMULT?;"
            ":WFMOUTPRE:YOFF?;:WFMOUTPRE:YZERO?;:WFMOUTPRE:PT_OFF?;"
            ":WFMOUTPRE:BYT_NR?;:WFMOUTPRE:BN_FMT?;:WFMOUTPRE:BYT_OR?;"
            ":WFMOUTPRE:PT_FMT?;:WFMOUTPRE:XUNIT?;:WFMOUTPRE:YUNIT?"
        )
        fields = preamble_response.split(";")
        if len(fields) != 12:
            raise ValueError(f"Unexpected WFMOUTPRE response ({len(fields)} fields): {preamble_response}")
        preamble = WaveformPreamble(
            x_increment=_float(fields[0]),
            x_zero=_float(fields[1]),
            y_multiplier=_float(fields[2]),
            y_offset=_float(fields[3]),
            y_zero=_float(fields[4]),
            point_offset=_float(fields[5]),
            byte_width=int(_float(fields[6])),
            binary_format=_strip(fields[7]),
            byte_order=_strip(fields[8]),
            point_format=_strip(fields[9]),
            x_unit=_strip(fields[10]),
            y_unit=_strip(fields[11]),
        )
        if preamble.point_format.upper() != "Y":
            raise ValueError(f"Expected Y waveform point format, received {preamble.point_format}")
        return parse_waveform(channel, self.query_raw("CURVE?"), preamble)  # SCPI: CURVe?

    def save_waveform_data(self, channel: int) -> Waveform:
        return self.waveform(channel, full_resolution=True)

    def all_events(self) -> str:
        return self.query("ALLEV?")  # SCPI: ALLEv?

    def event_count(self) -> int:
        return int(_float(self.query("EVQTY?")))  # SCPI: EVQty?

    def clear_status(self) -> None:
        self.write("*CLS")  # SCPI: *CLS

    def snapshot(self) -> dict[str, Any]:
        return {
            "channels": {channel: self.channel_state(channel) for channel in self.CHANNELS},
            "horizontal": self.horizontal_state(),
            "acquisition": self.acquisition_state(),
            "trigger": self.trigger_state(),
            "zoom": self.zoom_state(),
        }

    @staticmethod
    def waveform_dict(waveform: Waveform) -> dict[str, Any]:
        return {
            "channel": waveform.channel,
            "time": waveform.time,
            "voltage": waveform.voltage,
            "preamble": asdict(waveform.preamble),
        }
