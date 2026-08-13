from __future__ import annotations

import csv
import math
import time

from PySide6 import QtCore

from .controller import OscilloscopeController
from .instrument.mso2024 import MEASUREMENT_TYPES


VERTICAL_STEPS = tuple(v * 10.0**p for p in range(-3, 1) for v in (2.0, 5.0, 10.0) if 0.002 <= v * 10.0**p <= 5.0)
TIME_STEPS = tuple(v * 10.0**p for p in range(-9, 3) for v in (1.0, 2.0, 5.0) if 2e-9 <= v * 10.0**p <= 100.0)
MEASUREMENT_CHOICES = tuple(MEASUREMENT_TYPES)
TRIGGER_CHOICES = ("Edge", "Pulse Width", "Runt", "Logic", "Setup/Hold", "Rise/Fall Time", "Video", "Serial Bus (option)")
SEARCH_CHOICES = tuple(value for value in TRIGGER_CHOICES if value != "Video")
TRIGGER_TIME_CHOICES = {
    "20 ns": 20e-9,
    "50 ns": 50e-9,
    "100 ns": 100e-9,
    "500 ns": 500e-9,
    "1 us": 1e-6,
    "10 us": 10e-6,
    "100 us": 100e-6,
    "1 ms": 1e-3,
}
LOGIC_PATTERNS = {
    "H L X X": ("HIGH", "LOW", "X", "X"),
    "L H X X": ("LOW", "HIGH", "X", "X"),
    "H H H H": ("HIGH", "HIGH", "HIGH", "HIGH"),
    "L L L L": ("LOW", "LOW", "LOW", "LOW"),
}
DIGITAL_LOGIC_PATTERNS = {
    "D0:H D1:L": ("HIGH", "LOW", "X", "X"),
    "D0:L D1:H": ("LOW", "HIGH", "X", "X"),
    "D0-D3 High": ("HIGH", "HIGH", "HIGH", "HIGH"),
    "D0-D3 Low": ("LOW", "LOW", "LOW", "LOW"),
    "D0-D3 X": ("X", "X", "X", "X"),
}
SETUP_HOLD_CHOICES = {
    "1 ns / 1 ns": (1e-9, 1e-9),
    "5 ns / 5 ns": (5e-9, 5e-9),
    "10 ns / 10 ns": (10e-9, 10e-9),
    "50 ns / 50 ns": (50e-9, 50e-9),
}


def _step(values, current, direction):
    nearest = min(range(len(values)), key=lambda i: abs(math.log(values[i] / current)))
    return values[max(0, min(len(values) - 1, nearest - (1 if direction > 0 else -1)))]


class ScopeController(QtCore.QObject):
    stateChanged = QtCore.Signal()
    waveformChanged = QtCore.Signal()
    menuChanged = QtCore.Signal()
    diagnosticsChanged = QtCore.Signal()
    connectionUiChanged = QtCore.Signal()
    fileDialogRequested = QtCore.Signal(str)

    def __init__(self, simulation=False, parent=None):
        super().__init__(parent)
        self._simulation = simulation
        self._connected = simulation
        self._identity = "TEKTRONIX,MSO2024,SIMULATION,1.0" if simulation else ""
        self._resource = "SIM::MSO2024" if simulation else ""
        self._resources, self._searching = [], False
        self._selected, self._enabled = 1, [True, False, False, False]
        self._scales, self._positions = [0.5] * 4, [0.0] * 4
        self._time_scale, self._horizontal_delay, self._trigger_level, self._running = 1e-3, 0.0, 0.0, True
        self._menu, self._menu_selection = "channel", 0
        self._side_selection = 0
        self._couplings = ["DC"] * 4
        self._bandwidths = ["Full"] * 4
        self._attenuations = [10.0] * 4
        self._inverted = [False] * 4
        self._trigger_kind, self._trigger_source = "Edge", "CH1"
        self._trigger_coupling, self._trigger_slope, self._trigger_mode = "DC", "RISE", "AUTO"
        self._pulse_polarity, self._pulse_condition, self._pulse_time = "Positive", "Less Than", 1e-6
        self._logic_pattern, self._logic_function, self._logic_when = "H L X X", "AND", "True"
        self._logic_clock, self._logic_clock_edge, self._logic_time = "None", "Rising", 1e-6
        self._logic_digital_pattern, self._logic_threshold_source, self._logic_threshold = "D0-D3 X", "D0", 1.4
        self._setup_clock, self._setup_clock_edge, self._setup_data = "CH1", "Rising", "CH2"
        self._setup_clock_threshold = self._setup_data_threshold = 0.0
        self._setup_time, self._hold_time = 1e-9, 1e-9
        self._video_polarity, self._video_standard = "Positive", "NTSC"
        self._acquisition_mode, self._record_length = "SAMPLE", 100_000
        self._measurement_source, self._measurement_source2 = "CH1", "CH2"
        self._measurement_indicator, self._measurement_gating, self._measurement_method = "Off", "Screen", "Auto"
        self._measurements = [{"slot": i, "enabled": False} for i in range(1, 5)]
        self._cursor_state = {"function": "OFF", "x1": -0.001, "x2": 0.001, "y1": -0.5, "y2": 0.5}
        self._zoom_enabled, self._zoom_scale, self._zoom_position = False, 0.01, 50.0
        self._inspector_playing = False
        self._search_enabled, self._search_kind = False, "Edge"
        self._search_source, self._search_slope, self._search_level = "CH1", "Rising", 0.0
        self._search_polarity, self._search_condition, self._search_time = "Positive", "Less Than", 1e-6
        self._search_pattern, self._search_logic_when = "H L X X", "True"
        self._search_clock, self._search_clock_edge, self._search_data = "CH1", "Rising", "CH2"
        self._search_clock_threshold = self._search_data_threshold = 0.0
        self._search_setup_time, self._search_hold_time = 1e-9, 1e-9
        self._language, self._math_expression = "English", "CH1+CH2"
        self._references, self._bus = [False, False], 1
        self._reference_waveform = []
        self._bus_type = "Parallel"
        self._capabilities = {"parallel": True, "DPO2EMBD": simulation, "DPO2AUTO": simulation, "DPO2COMP": simulation}
        self._waveforms = [[] for _ in range(4)]
        self._last_tx = self._last_rx = self._error = ""
        self._acquisition_rate = self._transfer_ms = 0.0
        self._waveform_points = self._render_frames = 0
        self._render_rate, self._render_epoch = 0.0, time.perf_counter()
        self._phase, self._pending = 0.0, {}
        self._backend = None if simulation else OscilloscopeController(self)
        self._flush_timer = QtCore.QTimer(self, interval=55, singleShot=True)
        self._flush_timer.timeout.connect(self._flush_commands)
        self._wave_timer = QtCore.QTimer(self, interval=33)
        self._wave_timer.timeout.connect(self._simulate_frame)
        if simulation: self._wave_timer.start()
        else:
            self._wire_hardware()
            QtCore.QTimer.singleShot(100, self.scan)

    def _wire_hardware(self):
        worker = self._backend.worker
        worker.resources_found.connect(self._resources_found)
        worker.connection_changed.connect(self._connection_changed)
        worker.snapshot_ready.connect(self._snapshot)
        worker.waveform_ready.connect(self._waveform)
        worker.measurements_ready.connect(self._measurements_ready)
        worker.cursors_ready.connect(self._cursors_ready)
        worker.diagnostics.connect(self._diagnostics)
        worker.operation_done.connect(self._operation_done)
        worker.error.connect(self._set_error)

    @QtCore.Property(bool, notify=stateChanged)
    def connected(self): return self._connected
    @QtCore.Property(bool, notify=stateChanged)
    def simulation(self): return self._simulation
    @QtCore.Property(str, notify=stateChanged)
    def identity(self): return self._identity
    @QtCore.Property(int, notify=stateChanged)
    def selectedChannel(self): return self._selected
    @QtCore.Property(float, notify=stateChanged)
    def timeScale(self): return self._time_scale
    @QtCore.Property(float, notify=stateChanged)
    def triggerLevel(self): return self._trigger_level
    @QtCore.Property(str, notify=stateChanged)
    def triggerSource(self): return self._trigger_source
    @QtCore.Property(float, notify=stateChanged)
    def horizontalDelay(self): return self._horizontal_delay
    @QtCore.Property(bool, notify=stateChanged)
    def running(self): return self._running
    @QtCore.Property(str, notify=menuChanged)
    def menuContext(self): return self._menu
    @QtCore.Property(int, notify=menuChanged)
    def menuSelection(self): return self._menu_selection
    @QtCore.Property('QVariantList', notify=menuChanged)
    def bottomMenu(self): return self._bottom_menu()
    @QtCore.Property('QVariantList', notify=menuChanged)
    def sideMenu(self):
        return [{"label": value, "selected": i == self._side_selection, "enabled": self._choice_available(value), "reason": self._choice_reason(value)} for i, value in enumerate(self._side_choices())]
    @QtCore.Property(str, notify=menuChanged)
    def sideMenuTitle(self):
        menu = self._bottom_menu()
        return menu[self._menu_selection]["title"] if menu and self._menu_selection < len(menu) else ""
    @QtCore.Property(bool, notify=menuChanged)
    def sideMenuVisible(self): return bool(self._side_choices())
    @QtCore.Property(str, notify=menuChanged)
    def knobALabel(self): return "Measurement Type" if self._menu == "measure" and self._menu_selection == 0 else self.sideMenuTitle
    @QtCore.Property(str, notify=menuChanged)
    def knobAValue(self):
        choices = self._side_choices()
        return choices[self._side_selection] if choices else "Unassigned"
    @QtCore.Property(str, notify=menuChanged)
    def knobBLabel(self):
        if self._menu == "measure" and self._menu_selection == 0:
            return "Sources" if self._selected_measurement_type() in {"Delay", "Phase"} else "Source"
        return "Unassigned"
    @QtCore.Property(str, notify=menuChanged)
    def knobBValue(self):
        if self._menu == "measure" and self._menu_selection == 0:
            return f"{self._measurement_source} → {self._measurement_source2}" if self._selected_measurement_type() in {"Delay", "Phase"} else self._measurement_source
        return "—"
    @QtCore.Property('QVariantList', notify=stateChanged)
    def measurementReadouts(self):
        result = []
        for item in self._measurements:
            if not item.get("enabled"): continue
            result.append({"slot": item["slot"], "type": item.get("type", ""), "source": item.get("source", ""), "value": item.get("value", "—"), "unit": item.get("unit", "")})
        return result
    @QtCore.Property(str, notify=stateChanged)
    def cursorFunction(self): return self._cursor_state.get("function", "OFF")
    @QtCore.Property(float, notify=stateChanged)
    def cursorX1(self): return float(self._cursor_state.get("x1", 0.0))
    @QtCore.Property(float, notify=stateChanged)
    def cursorX2(self): return float(self._cursor_state.get("x2", 0.0))
    @QtCore.Property(float, notify=stateChanged)
    def cursorY1(self): return float(self._cursor_state.get("y1", 0.0))
    @QtCore.Property(float, notify=stateChanged)
    def cursorY2(self): return float(self._cursor_state.get("y2", 0.0))
    @QtCore.Property(bool, notify=stateChanged)
    def zoomEnabled(self): return self._zoom_enabled
    @QtCore.Property(float, notify=stateChanged)
    def zoomScale(self): return self._zoom_scale
    @QtCore.Property(float, notify=stateChanged)
    def zoomPosition(self): return self._zoom_position
    @QtCore.Property(bool, notify=stateChanged)
    def inspectorPlaying(self): return self._inspector_playing
    @QtCore.Property('QVariantList', notify=waveformChanged)
    def waveforms(self): return self._waveforms
    @QtCore.Property('QVariantList', notify=waveformChanged)
    def referenceWaveform(self): return self._reference_waveform
    @QtCore.Property(bool, notify=stateChanged)
    def referenceVisible(self): return self._references[0]
    @QtCore.Property(int, notify=diagnosticsChanged)
    def waveformPointCount(self): return self._waveform_points
    @QtCore.Property(str, notify=diagnosticsChanged)
    def diagnosticsText(self):
        return (f"Instrument: {self._identity or 'none'}\nResource: {self._resource or 'none'}\n"
                f"Last SCPI TX: {self._last_tx or '-'}\nLast SCPI RX: {self._last_rx or '-'}\n"
                f"SCPI Queue: {len(self._pending)}\nAcquisition: {self._acquisition_rate:.1f} waveforms/s\n"
                f"Waveform Points: {self._waveform_points}\nTransfer: {self._transfer_ms:.1f} ms\n"
                f"Render Updates: {self._render_rate:.1f} fps\nError: {self._error or '-'}")
    @QtCore.Property('QVariantList', notify=connectionUiChanged)
    def resources(self): return self._resources
    @QtCore.Property(bool, notify=connectionUiChanged)
    def searching(self): return self._searching

    @QtCore.Slot(int, result=bool)
    def channelEnabled(self, channel): return self._enabled[channel - 1]
    @QtCore.Slot(int, result=float)
    def channelScale(self, channel): return self._scales[channel - 1]
    @QtCore.Slot(int, result=float)
    def channelPosition(self, channel): return self._positions[channel - 1]

    def _bottom_menu(self):
        ch = self._selected - 1
        if self._menu == "channel":
            return [{"title": "Coupling", "value": self._couplings[ch]}, {"title": "Bandwidth", "value": self._bandwidths[ch]}, {"title": "Probe", "value": f"{self._attenuations[ch]:g}X"}, {"title": "Invert", "value": "On" if self._inverted[ch] else "Off"}, {"title": "Label", "value": f"CH{self._selected}"}, {"title": "More", "value": ""}]
        if self._menu == "trigger":
            return self._trigger_menu()
        if self._menu == "acquire":
            return [{"title": "Mode", "value": self._acquisition_mode.title()}, {"title": "Record", "value": "1M" if self._record_length == 1_000_000 else "100k"}, {"title": "Delay", "value": "Off"}, {"title": "Position", "value": "0 s"}, {"title": "Waveform", "value": "Display"}, {"title": "Details", "value": "Acquire"}]
        if self._menu == "measure":
            return [{"title": "Add", "value": "Measurement"}, {"title": "Remove", "value": "Measurement"}, {"title": "Indicators", "value": self._measurement_indicator}, {"title": "Gating", "value": self._measurement_gating}, {"title": "High-Low", "value": self._measurement_method}, {"title": "Cursors", "value": "Configure"}]
        if self._menu == "cursor":
            cursor_label = {"OFF": "Off", "VBARS": "Vertical Bars", "HBARS": "Horizontal Bars", "SCREEN": "Screen", "WAVEFORM": "Waveform"}.get(self.cursorFunction, self.cursorFunction)
            return [{"title": "Function", "value": cursor_label}, {"title": "Bring On", "value": "Screen"}, {"title": "Link", "value": "Off"}, {"title": "Source", "value": f"CH{self._selected}"}, {"title": "Units", "value": "Base"}, {"title": "", "value": ""}]
        if self._menu == "search":
            return self._search_menu()
        if self._menu == "test":
            return [{"title": "Application Test", "value": "Option dependent"}, {"title": "Control", "value": "Instrument menu"}]
        if self._menu == "utility":
            return [{"title": "Utility Page", "value": "Config"}, {"title": "Language", "value": self._language}, {"title": "Set Date & Time", "value": ""}, {"title": "TekSecure", "value": "Erase Memory"}, {"title": "About", "value": ""}]
        if self._menu == "save":
            return [{"title": "Save Screen", "value": "Image"}, {"title": "Save", "value": "Waveform"}, {"title": "Save", "value": "Setup"}, {"title": "Recall", "value": "Waveform"}, {"title": "Recall", "value": "Setup"}, {"title": "Assign Save", "value": "Setup"}, {"title": "File", "value": "Utilities"}]
        if self._menu == "math":
            return [{"title": "Dual Wfm", "value": "Math"}, {"title": "FFT", "value": ""}, {"title": "M", "value": "Label"}]
        if self._menu == "reference":
            return [{"title": "R1", "value": "On" if self._references[0] else "Off"}, {"title": "R2", "value": "On" if self._references[1] else "Off"}]
        if self._menu == "bus":
            return [{"title": f"B{self._bus}", "value": self._bus_type}, {"title": "Define", "value": "Inputs"}, {"title": "Thresholds", "value": ""}, {"title": f"B{self._bus}", "value": "Label"}, {"title": "Bus", "value": "Display"}, {"title": "Event", "value": "Table"}]
        return []

    def _trigger_menu(self):
        mode = {"title": "Mode/Holdoff", "value": self._trigger_mode.title()}
        if self._trigger_kind == "Edge":
            return [{"title": "Type", "value": self._trigger_kind}, {"title": "Source", "value": self._trigger_source}, {"title": "Coupling", "value": self._trigger_coupling}, {"title": "Slope", "value": "Rising" if self._trigger_slope == "RISE" else "Falling"}, {"title": "Level", "value": f"{self._trigger_level:.2f} V"}, mode]
        if self._trigger_kind in {"Pulse Width", "Runt", "Rise/Fall Time"}:
            quantity = "Delta Time" if self._trigger_kind == "Rise/Fall Time" else "Width"
            return [{"title": "Type", "value": self._trigger_kind}, {"title": "Source", "value": self._trigger_source}, {"title": "Polarity", "value": self._pulse_polarity}, {"title": "Trigger When", "value": self._pulse_condition}, {"title": quantity, "value": self._format_trigger_time(self._pulse_time)}, mode]
        if self._trigger_kind == "Logic":
            threshold = f"{self._logic_threshold_source} {self._logic_threshold:g} V"
            return [{"title": "Type", "value": self._trigger_kind}, {"title": "Analog", "value": self._logic_pattern}, {"title": "Digital", "value": self._logic_digital_pattern}, {"title": "Function", "value": self._logic_function}, {"title": "Trigger When", "value": self._logic_when}, {"title": "Threshold", "value": threshold}, mode]
        if self._trigger_kind == "Setup/Hold":
            times = f"{self._format_trigger_time(self._setup_time)} / {self._format_trigger_time(self._hold_time)}"
            clock = f"{self._setup_clock} {self._setup_clock_threshold:g} V"
            data = f"{self._setup_data} {self._setup_data_threshold:g} V"
            return [{"title": "Type", "value": self._trigger_kind}, {"title": "Clock", "value": clock}, {"title": "Clock Edge", "value": self._setup_clock_edge}, {"title": "Data", "value": data}, {"title": "Setup / Hold", "value": times}, mode]
        if self._trigger_kind == "Video":
            return [{"title": "Type", "value": self._trigger_kind}, {"title": "Source", "value": self._trigger_source}, {"title": "Polarity", "value": self._video_polarity}, {"title": "Standard", "value": self._video_standard}, {"title": "Level", "value": f"{self._trigger_level:.2f} V"}, mode]
        return [{"title": "Type", "value": self._trigger_kind}, {"title": "Bus Source", "value": f"B{self._bus}"}, {"title": "Trigger On", "value": "Bus Event"}, {"title": "Qualifier", "value": "Instrument"}, {"title": "Status", "value": "Option dependent"}, mode]

    def _search_menu(self):
        enabled = {"title": "Search", "value": "On" if self._search_enabled else "Off"}
        kind = {"title": "Type", "value": self._search_kind}
        actions = {"title": "Actions", "value": "Copy"}
        if self._search_kind == "Edge":
            return [enabled, kind, {"title": "Source", "value": self._search_source}, {"title": "Slope", "value": self._search_slope}, {"title": "Level", "value": f"{self._search_level:.2f} V"}, actions]
        if self._search_kind in {"Pulse Width", "Runt", "Rise/Fall Time"}:
            quantity = "Delta Time" if self._search_kind == "Rise/Fall Time" else "Width"
            return [enabled, kind, {"title": "Source", "value": self._search_source}, {"title": "Polarity", "value": self._search_polarity}, {"title": "When", "value": self._search_condition}, {"title": quantity, "value": self._format_trigger_time(self._search_time)}, actions]
        if self._search_kind == "Logic":
            return [enabled, kind, {"title": "Pattern", "value": self._search_pattern}, {"title": "When", "value": self._search_logic_when}, {"title": "Time", "value": self._format_trigger_time(self._search_time)}, actions]
        if self._search_kind == "Setup/Hold":
            times = f"{self._format_trigger_time(self._search_setup_time)} / {self._format_trigger_time(self._search_hold_time)}"
            return [enabled, kind, {"title": "Clock", "value": self._search_clock}, {"title": "Edge", "value": self._search_clock_edge}, {"title": "Data", "value": self._search_data}, {"title": "Setup / Hold", "value": times}, actions]
        return [enabled, kind, {"title": "Bus Source", "value": f"B{self._bus}"}, actions]

    @staticmethod
    def _format_trigger_time(seconds):
        for label, value in TRIGGER_TIME_CHOICES.items():
            if math.isclose(seconds, value): return label
        if seconds < 1e-6: return f"{seconds * 1e9:g} ns"
        if seconds < 1e-3: return f"{seconds * 1e6:g} us"
        return f"{seconds * 1e3:g} ms"

    def _side_choices(self):
        index = self._menu_selection
        if self._menu == "channel":
            return {0: ("DC", "AC", "GND"), 1: ("Full", "20 MHz"), 2: ("1X", "10X", "100X", "1000X"), 3: ("Off", "On")}.get(index, ())
        if self._menu == "trigger":
            return self._trigger_side_choices(index)
        if self._menu == "acquire": return {0: ("Sample", "Average"), 1: ("100k", "1M")}.get(index, ())
        if self._menu == "measure":
            if index == 0: return MEASUREMENT_CHOICES
            if index == 1: return tuple(f"Measurement {item['slot']}" for item in self._measurements if item.get("enabled")) + (("Remove All",) if any(item.get("enabled") for item in self._measurements) else ())
            if index == 2: return ("Off",) + tuple(f"Measurement {item['slot']}" for item in self._measurements if item.get("enabled"))
            if index == 3: return ("Off", "Screen", "Cursors")
            if index == 4: return ("Auto", "Histogram", "Min-Max")
        if self._menu == "cursor" and index == 0: return ("Off", "Vertical Bars", "Horizontal Bars", "Screen", "Waveform")
        if self._menu == "search":
            return self._search_side_choices(index)
        if self._menu == "utility":
            if index == 0: return ("Config", "I/O", "Calibration")
            if index == 1: return ("English", "French", "German", "Italian", "Spanish", "Portuguese", "Russian", "Japanese", "Korean", "Simplified Chinese", "Traditional Chinese")
        if self._menu == "save" and index in {2, 4}: return tuple(f"Slot {i}" for i in range(1, 11))
        if self._menu == "math":
            if index == 0: return ("CH1+CH2", "CH1-CH2", "CH1*CH2", "CH3+CH4", "CH3-CH4", "CH3*CH4")
            if index == 1: return ("FFT(CH1)", "FFT(CH2)", "FFT(CH3)", "FFT(CH4)")
        if self._menu == "reference" and index in {0, 1}: return ("Off", "On")
        if self._menu == "bus" and index == 0: return ("Parallel", "I2C", "SPI", "CAN", "LIN", "RS-232")
        return ()

    def _trigger_side_choices(self, index):
        if index == 0: return TRIGGER_CHOICES
        if index == (6 if self._trigger_kind == "Logic" else 5): return ("Auto", "Normal")
        if self._trigger_kind == "Edge":
            return {1: ("CH1", "CH2", "CH3", "CH4"), 2: ("DC", "HF Reject", "LF Reject", "Noise Reject"), 3: ("Rising", "Falling")}.get(index, ())
        if self._trigger_kind in {"Pulse Width", "Runt", "Rise/Fall Time"}:
            conditions = {
                "Pulse Width": ("Less Than", "More Than", "Equal", "Not Equal"),
                "Runt": ("Occurs", "Less Than", "More Than", "Equal", "Not Equal"),
                "Rise/Fall Time": ("Slower", "Faster", "Equal", "Not Equal"),
            }[self._trigger_kind]
            polarities = ("Positive", "Negative", "Either") if self._trigger_kind != "Pulse Width" else ("Positive", "Negative")
            return {1: ("CH1", "CH2", "CH3", "CH4"), 2: polarities, 3: conditions, 4: tuple(TRIGGER_TIME_CHOICES)}.get(index, ())
        if self._trigger_kind == "Logic":
            thresholds = tuple(f"D{channel} {level:g} V" for channel in range(16) for level in (1.4, -1.3))
            return {1: tuple(LOGIC_PATTERNS), 2: tuple(DIGITAL_LOGIC_PATTERNS), 3: ("AND", "NAND"), 4: ("True", "False", "Less Than", "More Than", "Equal", "Not Equal"), 5: thresholds}.get(index, ())
        if self._trigger_kind == "Setup/Hold":
            analog = ("CH1", "CH2", "CH3", "CH4")
            def sources(excluded):
                return tuple(source for source in analog if source != excluded) + tuple(
                    f"D{channel} {level:g} V"
                    for channel in range(16)
                    if f"D{channel}" != excluded
                    for level in (1.4, -1.3)
                )
            return {1: sources(self._setup_data), 2: ("Rising", "Falling"), 3: sources(self._setup_clock), 4: tuple(SETUP_HOLD_CHOICES)}.get(index, ())
        if self._trigger_kind == "Video":
            return {1: ("CH1", "CH2", "CH3", "CH4"), 2: ("Positive", "Negative"), 3: ("NTSC", "PAL", "SECAM")}.get(index, ())
        if self._trigger_kind == "Serial Bus (option)" and index == 1: return ("B1", "B2")
        return ()

    def _search_side_choices(self, index):
        actions = ("Copy to Trigger", "Copy from Trigger")
        if index == 0: return ("Off", "On")
        if index == 1: return SEARCH_CHOICES
        if self._search_kind == "Edge":
            return {2: ("CH1", "CH2", "CH3", "CH4", "MATH"), 3: ("Rising", "Falling"), 4: ("-2 V", "-1 V", "0 V", "1 V", "2 V"), 5: actions}.get(index, ())
        if self._search_kind in {"Pulse Width", "Runt", "Rise/Fall Time"}:
            conditions = {
                "Pulse Width": ("Less Than", "More Than", "Equal", "Not Equal"),
                "Runt": ("Occurs", "Less Than", "More Than", "Equal", "Not Equal"),
                "Rise/Fall Time": ("Slower", "Faster", "Equal", "Not Equal"),
            }[self._search_kind]
            polarities = ("Positive", "Negative") if self._search_kind == "Pulse Width" else ("Positive", "Negative", "Either")
            return {2: ("CH1", "CH2", "CH3", "CH4", "MATH"), 3: polarities, 4: conditions, 5: tuple(TRIGGER_TIME_CHOICES), 6: actions}.get(index, ())
        if self._search_kind == "Logic":
            return {2: tuple(LOGIC_PATTERNS), 3: ("True", "False", "Less Than", "More Than"), 4: tuple(TRIGGER_TIME_CHOICES), 5: actions}.get(index, ())
        if self._search_kind == "Setup/Hold":
            clocks = ("CH1", "CH2", "CH3", "CH4", "MATH", "REF")
            data = clocks + tuple(f"D{channel}" for channel in range(16))
            return {2: tuple(source for source in clocks if source != self._search_data), 3: ("Rising", "Falling"), 4: tuple(source for source in data if source != self._search_clock), 5: tuple(SETUP_HOLD_CHOICES), 6: actions}.get(index, ())
        if self._search_kind == "Serial Bus (option)":
            return {2: ("B1", "B2"), 3: actions}.get(index, ())
        return ()

    def _selected_measurement_type(self):
        if not MEASUREMENT_CHOICES: return ""
        return MEASUREMENT_CHOICES[min(self._side_selection, len(MEASUREMENT_CHOICES) - 1)]

    def _choice_available(self, value):
        module = {"I2C": "DPO2EMBD", "SPI": "DPO2EMBD", "CAN": "DPO2AUTO", "LIN": "DPO2AUTO", "RS-232": "DPO2COMP"}.get(value)
        if value == "Serial Bus (option)": return any(self._capabilities[name] for name in ("DPO2EMBD", "DPO2AUTO", "DPO2COMP"))
        return module is None or self._capabilities[module]

    def _choice_reason(self, value):
        module = {"I2C": "DPO2EMBD", "SPI": "DPO2EMBD", "CAN": "DPO2AUTO", "LIN": "DPO2AUTO", "RS-232": "DPO2COMP"}.get(value)
        return "" if not module or self._capabilities[module] else f"Requires {module} application module"

    @QtCore.Slot(int)
    def selectChannel(self, channel):
        if 1 <= channel <= 4:
            self._selected, self._enabled[channel - 1] = channel, True
            self._menu, self._menu_selection = "channel", 0
            self.stateChanged.emit(); self.menuChanged.emit()
            self._queue(f"enable{channel}", "set_channel_enabled", [channel, True])

    @QtCore.Slot(int)
    def pressChannel(self, channel):
        if not 1 <= channel <= 4: return
        if channel == self._selected and self._enabled[channel - 1]:
            self._enabled[channel - 1] = False
            self._queue(f"enable{channel}", "set_channel_enabled", [channel, False])
            self.stateChanged.emit()
        else:
            self.selectChannel(channel)

    @QtCore.Slot(int, int)
    def adjustChannelScale(self, channel, direction):
        attenuation = self._attenuations[channel - 1]
        steps = tuple(value * attenuation for value in VERTICAL_STEPS)
        self._scales[channel - 1] = _step(steps, self._scales[channel - 1], direction)
        self.stateChanged.emit(); self._queue(f"scale{channel}", "set_vertical_scale", [channel, self._scales[channel - 1]])

    @QtCore.Slot(int, int, bool)
    def adjustChannelPosition(self, channel, direction, fine=False):
        delta = 0.02 if fine else 0.1
        self._positions[channel - 1] = max(-4.0, min(4.0, self._positions[channel - 1] + direction * delta))
        self.stateChanged.emit(); self._queue(f"position{channel}", "set_vertical_position", [channel, self._positions[channel - 1]])

    @QtCore.Slot(int, float)
    def setChannelPosition(self, channel, position):
        self._positions[channel - 1] = max(-4.0, min(4.0, position))
        self.stateChanged.emit(); self._queue(f"position{channel}", "set_vertical_position", [channel, self._positions[channel - 1]])

    @QtCore.Slot(int)
    def adjustTimeScale(self, direction):
        self._time_scale = _step(TIME_STEPS, self._time_scale, direction)
        self.stateChanged.emit(); self._queue("time", "set_time_scale", [self._time_scale])

    @QtCore.Slot(float)
    def adjustHorizontalDelay(self, divisions):
        self._horizontal_delay += divisions * self._time_scale
        self.stateChanged.emit(); self._queue("horizontal_delay", "set_delay", [self._horizontal_delay])

    @QtCore.Slot(float)
    def setTriggerLevel(self, level):
        self._trigger_level = float(level)
        self.stateChanged.emit(); self.menuChanged.emit(); self._queue("trigger", "set_trigger_level", [self._selected, self._trigger_level])

    @QtCore.Slot(int, bool)
    def adjustTriggerLevel(self, direction, fine=False):
        self._trigger_level += direction * (0.01 if fine else 0.05)
        self.stateChanged.emit(); self._queue("trigger", "set_trigger_level", [self._selected, self._trigger_level])

    @QtCore.Slot()
    def centerTrigger(self):
        self._trigger_level = 0.0; self.stateChanged.emit(); self._queue("trigger", "set_trigger_level", [self._selected, 0.0])
    @QtCore.Slot()
    def resetView(self):
        self._positions[self._selected - 1] = 0.0
        self._horizontal_delay = 0.0
        self.stateChanged.emit()
        self._queue(f"position{self._selected}", "set_vertical_position", [self._selected, 0.0])
        self._queue("horizontal_position", "set_horizontal_position", [50.0])
    @QtCore.Slot(str)
    def openMenu(self, context): self._menu, self._menu_selection, self._side_selection = context, 0, 0; self.menuChanged.emit()
    @QtCore.Slot(int)
    def selectMenuItem(self, index): self._menu_selection, self._side_selection = index, 0; self.menuChanged.emit()
    @QtCore.Slot(int)
    def pressMenuItem(self, index):
        self.selectMenuItem(index)
        if self._menu == "acquire" and index == 3:
            self._horizontal_delay = 0.0; self.stateChanged.emit(); self._queue("horizontal_position", "set_horizontal_position", [50.0])
        elif self._menu == "reference" and index in {0, 1}:
            self._references[index] = not self._references[index]
            self._queue(f"reference{index+1}", "set_reference_enabled", [index + 1, self._references[index]])
            self.stateChanged.emit(); self.menuChanged.emit()
        elif self._menu == "measure" and index == 5:
            self.openMenu("cursor")
        elif self._menu == "save" and index in {0, 1, 3}:
            self.fileDialogRequested.emit({0: "screen-save", 1: "waveform-save", 3: "waveform-load"}[index])
    @QtCore.Slot(int)
    def selectSideItem(self, index):
        choices = self._side_choices()
        if 0 <= index < len(choices) and self._choice_available(choices[index]):
            self._side_selection = index
            self._apply_side_choice(choices[index])
            self.menuChanged.emit(); self.stateChanged.emit()
    @QtCore.Slot(str, int)
    def adjustMultipurpose(self, knob, direction):
        if knob == "B" and self._menu == "measure" and self._menu_selection == 0:
            sources = ("CH1", "CH2", "CH3", "CH4")
            if self._selected_measurement_type() in {"Delay", "Phase"}:
                pairs = tuple((source1, source2) for source1 in sources for source2 in sources if source1 != source2)
                i = pairs.index((self._measurement_source, self._measurement_source2))
                self._measurement_source, self._measurement_source2 = pairs[(i + direction) % len(pairs)]
            else:
                i = sources.index(self._measurement_source)
                self._measurement_source = sources[(i + direction) % len(sources)]
            self.menuChanged.emit(); return
        choices = self._side_choices()
        if choices:
            self._side_selection = (self._side_selection + direction) % len(choices)
            self.menuChanged.emit()
    @QtCore.Slot()
    def applyMultipurpose(self):
        choices = self._side_choices()
        if choices: self.selectSideItem(self._side_selection)
    @QtCore.Slot()
    def closeMenu(self): self._menu = ""; self.menuChanged.emit()
    @QtCore.Slot()
    def toggleRun(self):
        self._running = not self._running; self.stateChanged.emit(); self._queue("acquire", "run" if self._running else "stop", [])
    @QtCore.Slot()
    def single(self): self._running = False; self.stateChanged.emit(); self._queue("acquire", "single", [])
    @QtCore.Slot()
    def autoset(self): self._queue("autoset", "autoset", [])
    @QtCore.Slot()
    def forceTrigger(self): self._queue("force", "force_trigger", [])
    @QtCore.Slot()
    def openTestMenu(self):
        self.openMenu("test")
        self._queue("test_menu", "open_test_menu", [])
    @QtCore.Slot()
    def scan(self):
        if self._backend:
            self._searching = True; self.connectionUiChanged.emit(); self._backend.request_scan.emit()
    @QtCore.Slot()
    def reconnect(self): self.scan()
    @QtCore.Slot(str)
    def connectResource(self, resource):
        if self._backend:
            self._wave_timer.stop(); self._simulation = False
            self._backend.request_connect.emit(resource, 5000); self.stateChanged.emit()
    @QtCore.Slot()
    def enableSimulation(self):
        if self._backend and self._connected: self._backend.request_disconnect.emit()
        self._simulation, self._connected = True, True
        self._identity, self._resource, self._error = "TEKTRONIX,MSO2024,SIMULATION,1.0", "SIM::MSO2024", ""
        self._wave_timer.start(); self.stateChanged.emit(); self.diagnosticsChanged.emit()
    @QtCore.Slot(int)
    def openBusMenu(self, bus):
        if bus in {1, 2}: self._bus = bus; self.openMenu("bus")
    @QtCore.Slot()
    def defaultSetup(self):
        self._queue("default_setup", "default_setup", [])
    @QtCore.Slot(str, result=str)
    def localFilePath(self, url):
        parsed = QtCore.QUrl(url)
        return parsed.toLocalFile() if parsed.isLocalFile() else url
    @QtCore.Slot(str)
    def exportWaveform(self, url):
        path = self.localFilePath(url)
        if self._simulation:
            values = self._waveforms[self._selected - 1]
            if not values: return
            try:
                duration = self._time_scale * 10.0
                with open(path, "w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle); writer.writerow(("time_s", "voltage_V"))
                    denominator = max(1, len(values) - 1)
                    writer.writerows((((index / denominator) - 0.5) * duration, value) for index, value in enumerate(values))
                self._operation_done("waveform_exported", {"path": path, "points": len(values)})
            except OSError as exc: self._set_error(f"Waveform export: {exc}")
        elif self._backend:
            self._backend.request_export_waveform.emit(self._selected, path)
    @QtCore.Slot(str)
    def loadReferenceWaveform(self, url):
        path = self.localFilePath(url)
        values = []
        try:
            with open(path, newline="", encoding="utf-8-sig") as handle:
                reader = csv.reader(handle)
                for row in reader:
                    if len(row) < 2: continue
                    try: values.append(float(row[1]))
                    except ValueError: continue
        except OSError as exc:
            self._set_error(f"Waveform recall: {exc}"); return
        if not values:
            self._set_error("Waveform recall: CSV contains no numeric voltage column"); return
        self._reference_waveform = values[::max(1, len(values) // 1200)]
        self._references[0] = bool(self._reference_waveform)
        self._operation_done("waveform_loaded", {"path": path, "points": len(values)})
        self.waveformChanged.emit(); self.stateChanged.emit(); self.menuChanged.emit()
    @QtCore.Slot(str, str)
    def fileOperationCompleted(self, operation, url):
        self._operation_done(operation, {"path": self.localFilePath(url)})
    @QtCore.Slot(str, str)
    def fileOperationFailed(self, operation, url):
        self._set_error(f"{operation}: could not write {self.localFilePath(url)}")
    @QtCore.Slot(str, int, float)
    def setCursorPosition(self, axis, number, value):
        key = ("x" if axis == "VBARS" else "y") + str(number)
        self._cursor_state[key] = value
        self.stateChanged.emit(); self._queue(f"cursor_{axis}_{number}", "set_cursor_position", [axis, number, value])
    @QtCore.Slot()
    def toggleZoom(self):
        self._zoom_enabled = not self._zoom_enabled
        self.stateChanged.emit(); self._queue("zoom_enabled", "set_zoom_enabled", [self._zoom_enabled])
    @QtCore.Slot(int)
    def adjustZoom(self, direction):
        self._zoom_enabled = True
        self._zoom_scale = max(1e-3, min(5.0, self._zoom_scale * (0.8 if direction > 0 else 1.25)))
        self.stateChanged.emit(); self._queue("zoom_enabled", "set_zoom_enabled", [True]); self._queue("zoom_scale", "set_zoom_scale", [self._zoom_scale])
    @QtCore.Slot(int)
    def panZoom(self, direction):
        self._zoom_position = max(0.0, min(100.0, self._zoom_position + direction * 2.0))
        self.stateChanged.emit(); self._queue("zoom_position", "set_zoom_position", [self._zoom_position])
    @QtCore.Slot(str)
    def moveMark(self, direction): self._queue("mark_move", "move_to_mark", [direction])
    @QtCore.Slot()
    def createMark(self): self._queue("mark_create", "create_mark", [f"CH{self._selected}"])
    @QtCore.Slot()
    def toggleInspectorPlayback(self):
        self._inspector_playing = not self._inspector_playing
        self._zoom_enabled = True
        self.stateChanged.emit()
        self._queue("inspector_playback", "toggle_wave_inspector_playback", [])

    def _apply_side_choice(self, value):
        ch = self._selected - 1
        if self._menu == "channel":
            if self._menu_selection == 0:
                self._couplings[ch] = value; self._queue(f"coupling{ch}", "set_coupling", [ch + 1, value])
            elif self._menu_selection == 1:
                self._bandwidths[ch] = value; self._queue(f"bandwidth{ch}", "set_bandwidth", [ch + 1, value])
            elif self._menu_selection == 2:
                attenuation = float(value[:-1]); self._attenuations[ch] = attenuation; self._queue(f"probe{ch}", "set_probe_attenuation", [ch + 1, attenuation])
            elif self._menu_selection == 3:
                enabled = value == "On"; self._inverted[ch] = enabled; self._queue(f"invert{ch}", "set_invert", [ch + 1, enabled])
        elif self._menu == "trigger":
            if self._menu_selection == 0:
                self._trigger_kind = value
                if value == "Pulse Width" and self._pulse_polarity == "Either": self._pulse_polarity = "Positive"
                if value == "Rise/Fall Time": self._pulse_condition = "Slower"
                elif value == "Runt": self._pulse_condition = "Occurs"
                elif value == "Pulse Width": self._pulse_condition = "Less Than"
                self._queue("trigger_kind", "set_trigger_kind", [value])
            elif self._trigger_kind == "Edge" and self._menu_selection == 1:
                self._trigger_source = value; self._queue("trigger_source", "set_edge_source", [value])
            elif self._trigger_kind == "Edge" and self._menu_selection == 2:
                mapping = {"HF Reject": "HFREJ", "LF Reject": "LFREJ", "Noise Reject": "NOISEREJ"}
                self._trigger_coupling = value; self._queue("trigger_coupling", "set_edge_coupling", [mapping.get(value, value)])
            elif self._trigger_kind == "Edge" and self._menu_selection == 3:
                self._trigger_slope = "RISE" if value == "Rising" else "FALL"; self._queue("trigger_slope", "set_edge_slope", [self._trigger_slope])
            elif self._menu_selection == (6 if self._trigger_kind == "Logic" else 5):
                self._trigger_mode = value.upper(); self._queue("trigger_mode", "set_trigger_mode", [self._trigger_mode])
            elif self._trigger_kind in {"Pulse Width", "Runt", "Rise/Fall Time"}:
                if self._menu_selection == 1: self._trigger_source = value
                elif self._menu_selection == 2: self._pulse_polarity = value
                elif self._menu_selection == 3: self._pulse_condition = value
                elif self._menu_selection == 4: self._pulse_time = TRIGGER_TIME_CHOICES[value]
                if self._menu_selection == 1:
                    self._queue("pulse_source", "set_pulse_source", [self._trigger_kind, self._trigger_source])
                else:
                    self._queue_pulse_trigger()
            elif self._trigger_kind == "Logic":
                if self._menu_selection == 1: self._logic_pattern = value
                elif self._menu_selection == 2: self._logic_digital_pattern = value
                elif self._menu_selection == 3: self._logic_function = value
                elif self._menu_selection == 4: self._logic_when = value
                elif self._menu_selection == 5:
                    parts = value.split()
                    self._logic_threshold_source = parts[0]
                    self._logic_threshold = float(parts[1])
                self._queue_logic_trigger()
            elif self._trigger_kind == "Setup/Hold":
                if self._menu_selection == 1:
                    parts = value.split(); self._setup_clock = parts[0]
                    if len(parts) > 1: self._setup_clock_threshold = float(parts[1])
                elif self._menu_selection == 2: self._setup_clock_edge = value
                elif self._menu_selection == 3:
                    parts = value.split(); self._setup_data = parts[0]
                    if len(parts) > 1: self._setup_data_threshold = float(parts[1])
                elif self._menu_selection == 4: self._setup_time, self._hold_time = SETUP_HOLD_CHOICES[value]
                self._queue_setup_hold_trigger()
            elif self._trigger_kind == "Video":
                if self._menu_selection == 1: self._trigger_source = value
                elif self._menu_selection == 2: self._video_polarity = value
                elif self._menu_selection == 3: self._video_standard = value
                self._queue_video_trigger()
            elif self._trigger_kind == "Serial Bus (option)" and self._menu_selection == 1:
                self._bus = int(value[-1])
        elif self._menu == "acquire":
            if self._menu_selection == 0:
                self._acquisition_mode = value.upper(); self._queue("acquisition_mode", "set_acquisition_mode", [self._acquisition_mode, 16 if self._acquisition_mode == "AVERAGE" else None])
            elif self._menu_selection == 1:
                self._record_length = 1_000_000 if value == "1M" else 100_000; self._queue("record", "set_record_length", [self._record_length])
        elif self._menu == "measure":
            if self._menu_selection == 0:
                slot = next((item["slot"] for item in self._measurements if not item.get("enabled")), 1)
                item = {"slot": slot, "enabled": True, "type": value, "source": self._measurement_source, "value": "—", "unit": ""}
                self._measurements[slot - 1] = item
                source2 = self._measurement_source2 if value in {"Delay", "Phase"} else None
                self._queue(f"measurement{slot}", "configure_measurement", [slot, MEASUREMENT_TYPES[value], self._measurement_source, True, source2])
            elif self._menu_selection == 1:
                if value == "Remove All":
                    for item in self._measurements:
                        if item.get("enabled"): self._queue(f"measurement{item['slot']}", "disable_measurement", [item["slot"]])
                    self._measurements = [{"slot": i, "enabled": False} for i in range(1, 5)]
                else:
                    slot = int(value.rsplit(" ", 1)[1]); self._measurements[slot - 1] = {"slot": slot, "enabled": False}; self._queue(f"measurement{slot}", "disable_measurement", [slot])
            elif self._menu_selection == 2:
                self._measurement_indicator = value
                slot = None if value == "Off" else int(value.rsplit(" ", 1)[1])
                self._queue("measurement_indicators", "set_measurement_indicators", [slot])
            elif self._menu_selection == 3:
                self._measurement_gating = value
                self._queue("measurement_gating", "set_measurement_gating", ["CURSOR" if value == "Cursors" else value.upper()])
            elif self._menu_selection == 4:
                self._measurement_method = value
                self._queue("measurement_method", "set_measurement_method", ["MINMAX" if value == "Min-Max" else value.upper()])
        elif self._menu == "cursor" and self._menu_selection == 0:
            function = {"Off": "OFF", "Vertical Bars": "VBARS", "Horizontal Bars": "HBARS", "Screen": "SCREEN", "Waveform": "WAVEFORM"}[value]
            self._cursor_state["function"] = function
            self._queue("cursor_function", "set_cursor_function", [function])
        elif self._menu == "search":
            if self._menu_selection == 0:
                self._search_enabled = value == "On"; self._queue("search_enabled", "set_search_enabled", [self._search_enabled])
            elif self._menu_selection == 1:
                self._search_kind = value
                if value == "Pulse Width": self._search_polarity, self._search_condition = "Positive", "Less Than"
                elif value == "Runt": self._search_condition = "Occurs"
                elif value == "Rise/Fall Time": self._search_condition = "Slower"
                self._queue("search_kind", "set_search_kind", [value])
            elif value in {"Copy to Trigger", "Copy from Trigger"}:
                self._queue("search_copy", "copy_search_settings", [value == "Copy to Trigger"])
            elif self._search_kind == "Edge":
                if self._menu_selection == 2: self._search_source = value
                elif self._menu_selection == 3: self._search_slope = value
                elif self._menu_selection == 4: self._search_level = float(value.split()[0])
                self._queue_edge_search()
            elif self._search_kind in {"Pulse Width", "Runt", "Rise/Fall Time"}:
                if self._menu_selection == 2: self._search_source = value
                elif self._menu_selection == 3: self._search_polarity = value
                elif self._menu_selection == 4: self._search_condition = value
                elif self._menu_selection == 5: self._search_time = TRIGGER_TIME_CHOICES[value]
                self._queue_pulse_search()
            elif self._search_kind == "Logic":
                if self._menu_selection == 2: self._search_pattern = value
                elif self._menu_selection == 3: self._search_logic_when = value
                elif self._menu_selection == 4: self._search_time = TRIGGER_TIME_CHOICES[value]
                self._queue_logic_search()
            elif self._search_kind == "Setup/Hold":
                if self._menu_selection == 2: self._search_clock = value
                elif self._menu_selection == 3: self._search_clock_edge = value
                elif self._menu_selection == 4: self._search_data = value
                elif self._menu_selection == 5: self._search_setup_time, self._search_hold_time = SETUP_HOLD_CHOICES[value]
                self._queue_setup_hold_search()
            elif self._search_kind == "Serial Bus (option)" and self._menu_selection == 2:
                self._bus = int(value[-1]); self._queue("search_bus", "set_search_bus_source", [self._bus])
        elif self._menu == "utility" and self._menu_selection == 1:
            self._language = value; self._queue("language", "set_language", [value])
        elif self._menu == "save" and self._menu_selection in {2, 4}:
            slot = int(value.split()[-1]); method = "save_setup" if self._menu_selection == 2 else "recall_setup"
            self._queue("setup", method, [slot])
        elif self._menu == "math" and self._menu_selection in {0, 1}:
            self._math_expression = value; self._queue("math", "configure_math", [value])
        elif self._menu == "reference" and self._menu_selection in {0, 1}:
            reference = self._menu_selection + 1; enabled = value == "On"; self._references[reference - 1] = enabled
            self._queue(f"reference{reference}", "set_reference_enabled", [reference, enabled])
        elif self._menu == "bus" and self._menu_selection == 0:
            self._bus_type = value
            self._queue(f"bus{self._bus}_type", "set_bus_type", [self._bus, value])

    def _queue_pulse_trigger(self):
        condition = {"Less Than": "LESSTHAN", "More Than": "MORETHAN", "Not Equal": "UNEQUAL"}.get(self._pulse_condition, self._pulse_condition.upper())
        self._queue("pulse_parameter", "set_pulse_parameter", [self._trigger_kind, self._pulse_polarity.upper(), condition, self._pulse_time])

    def _queue_logic_trigger(self):
        inputs = LOGIC_PATTERNS[self._logic_pattern]
        digital_inputs = DIGITAL_LOGIC_PATTERNS[self._logic_digital_pattern]
        when = {"Less Than": "LESSTHAN", "More Than": "MORETHAN", "Not Equal": "UNEQUAL"}.get(self._logic_when, self._logic_when.upper())
        clock = "NONE" if self._logic_clock == "None" else self._logic_clock
        edge = {"Rising": "RISE", "Falling": "FALL", "Either": "EITHER"}.get(self._logic_clock_edge, self._logic_clock_edge.upper())
        self._queue("logic_trigger", "configure_logic_trigger", [*inputs, self._logic_function, when, self._logic_time, clock, edge, digital_inputs, self._logic_threshold_source, self._logic_threshold])

    def _queue_setup_hold_trigger(self):
        edge = "RISE" if self._setup_clock_edge == "Rising" else "FALL"
        self._queue("setup_hold_trigger", "configure_setup_hold_trigger", [self._setup_clock, edge, self._setup_clock_threshold, self._setup_data, self._setup_data_threshold, self._setup_time, self._hold_time])

    def _queue_video_trigger(self):
        self._queue("video_trigger", "set_video_trigger", [self._trigger_source, self._video_polarity.upper(), self._video_standard])

    def _queue_edge_search(self):
        slope = "RISE" if self._search_slope == "Rising" else "FALL"
        self._queue("edge_search", "configure_edge_search", [self._search_source, slope, self._search_level])

    def _queue_pulse_search(self):
        condition = {"Less Than": "LESSTHAN", "More Than": "MORETHAN", "Not Equal": "UNEQUAL"}.get(self._search_condition, self._search_condition.upper())
        self._queue("pulse_search", "configure_pulse_search", [self._search_kind, self._search_source, self._search_polarity.upper(), condition, self._search_time])

    def _queue_logic_search(self):
        inputs = LOGIC_PATTERNS[self._search_pattern]
        when = {"Less Than": "LESSTHAN", "More Than": "MORETHAN"}.get(self._search_logic_when, self._search_logic_when.upper())
        self._queue("logic_search", "configure_logic_search", [*inputs, when, self._search_time])

    def _queue_setup_hold_search(self):
        edge = "RISE" if self._search_clock_edge == "Rising" else "FALL"
        self._queue("setup_hold_search", "configure_setup_hold_search", [self._search_clock, edge, self._search_clock_threshold, self._search_data, self._search_data_threshold, self._search_setup_time, self._search_hold_time])

    def _queue(self, key, method, args):
        if not self._simulation: self._pending[key] = (method, args); self._flush_timer.start()
    def _flush_commands(self):
        commands, self._pending = self._pending, {}
        for method, args in commands.values(): self._last_tx = method; self._backend.request_invoke.emit(method, args)
        self.diagnosticsChanged.emit()
    def _resources_found(self, records):
        self._resources, self._searching = list(records), False; self.connectionUiChanged.emit()
        match = next((r for r in records if r.get("is_mso2024")), None)
        if match: self.connectResource(match["resource"])
        else: self._set_error("Tektronix MSO2024 not found")
    def _connection_changed(self, connected, identity, resource):
        if not connected and self._simulation: return
        self._connected, self._identity, self._resource = connected, identity, resource
        if connected:
            reported = identity.upper()
            bundle = "DPO2BND" in reported
            for module in ("DPO2EMBD", "DPO2AUTO", "DPO2COMP"):
                self._capabilities[module] = bundle or module in reported
        self._searching = False; self.stateChanged.emit(); self.menuChanged.emit(); self.connectionUiChanged.emit()
    def _snapshot(self, state):
        channels = state.get("channels", {})
        for ch in range(1, 5):
            item = channels.get(ch, channels.get(str(ch), {}))
            self._enabled[ch - 1] = bool(item.get("enabled", self._enabled[ch - 1]))
            self._scales[ch - 1] = float(item.get("scale", self._scales[ch - 1]))
            self._positions[ch - 1] = float(item.get("position", self._positions[ch - 1]))
            self._couplings[ch - 1] = str(item.get("coupling", self._couplings[ch - 1])).upper()
            bandwidth = str(item.get("bandwidth", self._bandwidths[ch - 1])).upper()
            self._bandwidths[ch - 1] = "20 MHz" if "TWENTY" in bandwidth else "Full"
            self._attenuations[ch - 1] = float(item.get("attenuation", self._attenuations[ch - 1]))
            self._inverted[ch - 1] = bool(item.get("invert", self._inverted[ch - 1]))
        self._time_scale = float(state.get("horizontal", {}).get("scale", self._time_scale))
        self._horizontal_delay = float(state.get("horizontal", {}).get("delay", self._horizontal_delay))
        self._running = bool(state.get("acquisition", {}).get("running", self._running))
        acquisition = state.get("acquisition", {})
        self._acquisition_mode = str(acquisition.get("mode", self._acquisition_mode)).upper()
        self._record_length = int(state.get("horizontal", {}).get("record_length", self._record_length))
        trigger = state.get("trigger", {})
        self._trigger_level = float(trigger.get("level", self._trigger_level))
        self._trigger_kind = str(trigger.get("kind", self._trigger_kind))
        self._trigger_source = str(trigger.get("source", self._trigger_source))
        self._trigger_slope = str(trigger.get("slope", self._trigger_slope))
        self._trigger_coupling = str(trigger.get("coupling", self._trigger_coupling))
        self._trigger_mode = str(trigger.get("mode", self._trigger_mode))
        self.stateChanged.emit(); self.menuChanged.emit()
    def _waveform(self, channel, _time, voltage, _preamble):
        values = voltage.tolist() if hasattr(voltage, "tolist") else list(voltage)
        self._waveforms[channel - 1] = values[::max(1, len(values) // 1200)]
        self._waveform_points = len(values); self._note_render(); self.waveformChanged.emit()
    def _measurements_ready(self, measurements):
        normalized = []
        for slot in range(1, 5):
            item = next((dict(value) for value in measurements if int(value.get("slot", 0)) == slot), {"slot": slot, "enabled": False})
            if item.get("enabled"):
                code = str(item.get("type", "")); item["type"] = next((label for label, value in MEASUREMENT_TYPES.items() if value == code), code.title())
                item["source"] = item.get("source", "")
            normalized.append(item)
        self._measurements = normalized; self.stateChanged.emit(); self.menuChanged.emit()
    def _cursors_ready(self, state):
        self._cursor_state.update(state); self.stateChanged.emit(); self.menuChanged.emit()
    def _diagnostics(self, data):
        self._last_tx, self._last_rx, self._error = data.get("last_command", ""), data.get("last_response", ""), data.get("error", "")
        self._acquisition_rate = float(data.get("acquisition_rate", self._acquisition_rate))
        self._waveform_points = int(data.get("waveform_points", self._waveform_points))
        self._transfer_ms = float(data.get("transfer_ms", self._transfer_ms))
        self.diagnosticsChanged.emit()
    def _operation_done(self, name, result):
        if isinstance(result, dict):
            path, points = result.get("path", ""), result.get("points")
            self._last_rx = f"{name}: {path}" + (f" ({points} points)" if points is not None else "")
        else: self._last_rx = f"{name}: {result}"
        self.diagnosticsChanged.emit()
    def _set_error(self, message): self._error = str(message); self.diagnosticsChanged.emit()
    def _simulate_frame(self):
        if self._inspector_playing:
            self._zoom_position = (self._zoom_position + 0.5) % 100.0
        if not self._running and any(self._waveforms): return
        self._phase += 0.045; count = 900; traces = []
        for channel in range(4):
            trace = []
            for i in range(count):
                x = i / (count - 1); angle = 2 * math.pi * (2 + channel) * x + self._phase
                if channel == 0: value = math.sin(angle)
                elif channel == 1: value = 0.75 if math.sin(angle) >= 0 else -0.75
                elif channel == 2: value = 2 * abs(2 * ((x * 3 + self._phase / 6) % 1) - 1) - 1
                else: value = 0.55 * math.sin(angle) + 0.16 * math.sin(angle * 11.3)
                trace.append(value * self._scales[channel] * 2 + self._positions[channel] * self._scales[channel])
            traces.append(trace)
        self._waveforms = traces; self._waveform_points = count; self._acquisition_rate = 30.0
        for item in self._measurements:
            if not item.get("enabled"): continue
            channel = int(str(item.get("source", "CH1"))[-1]) - 1
            frequency = (2 + channel) / (10 * self._time_scale)
            kind = item.get("type")
            if kind == "Frequency": item.update(value=f"{frequency:.4g}", unit="Hz")
            elif kind == "Period": item.update(value=f"{1/frequency:.4g}", unit="s")
            elif kind in {"Peak-to-Peak", "Amplitude"}: item.update(value=f"{4*self._scales[channel]:.4g}", unit="V")
            else: item.update(value=f"{self._scales[channel]:.4g}", unit="V")
        self._note_render(); self.waveformChanged.emit(); self.stateChanged.emit()
    def _note_render(self):
        self._render_frames += 1
        elapsed = time.perf_counter() - self._render_epoch
        if elapsed >= 1.0:
            self._render_rate = self._render_frames / elapsed
            self._render_frames, self._render_epoch = 0, time.perf_counter()
            self.diagnosticsChanged.emit()
    def close(self):
        if self._backend: self._backend.close()
