from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from ..instrument.mso2024 import TRIGGER_KINDS


class TriggerPanel(QtWidgets.QWidget):
    changed = QtCore.Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        common = QtWidgets.QFormLayout()
        self.kind = QtWidgets.QComboBox()
        self.kind.addItems(TRIGGER_KINDS.keys())
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(["AUTO", "NORMAL"])
        self.holdoff = QtWidgets.QDoubleSpinBox()
        self.holdoff.setDecimals(9)
        self.holdoff.setRange(20e-9, 8.0)
        self.holdoff.setValue(20e-9)
        self.holdoff.setSuffix(" s")
        self.holdoff.setKeyboardTracking(False)
        common.addRow("Type", self.kind)
        common.addRow("Mode", self.mode)
        common.addRow("Holdoff", self.holdoff)
        layout.addLayout(common)
        self.stack = QtWidgets.QStackedWidget()
        self.edge_page = self._edge_page()
        self.pulse_page = self._pulse_page()
        self.video_page = self._video_page()
        self.logic_page = self._logic_page()
        self.setup_hold_page = self._setup_hold_page()
        self.info_page = QtWidgets.QLabel()
        self.info_page.setWordWrap(True)
        self.info_page.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        for page in (
            self.edge_page,
            self.pulse_page,
            self.video_page,
            self.logic_page,
            self.setup_hold_page,
            self.info_page,
        ):
            self.stack.addWidget(page)
        layout.addWidget(self.stack)
        self.kind.currentTextChanged.connect(self._kind_changed)
        self.mode.currentTextChanged.connect(lambda value: self.changed.emit("set_trigger_mode", [value]))
        self.holdoff.valueChanged.connect(lambda value: self.changed.emit("set_trigger_holdoff", [value]))
        self._kind_changed(self.kind.currentText())

    @staticmethod
    def _sources(edge: bool = False) -> QtWidgets.QComboBox:
        combo = QtWidgets.QComboBox()
        combo.addItems(["CH1", "CH2", "CH3", "CH4"] + (["EXT", "LINE", "AUX"] if edge else []))
        return combo

    def _edge_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(page)
        self.edge_source = self._sources(edge=True)
        self.edge_level = QtWidgets.QDoubleSpinBox()
        self.edge_level.setRange(-1e6, 1e6)
        self.edge_level.setDecimals(6)
        self.edge_level.setSuffix(" V")
        self.edge_level.setKeyboardTracking(False)
        self.edge_slope = QtWidgets.QComboBox()
        self.edge_slope.addItems(["RISE", "FALL"])
        self.edge_coupling = QtWidgets.QComboBox()
        self.edge_coupling.addItems(["DC", "HFREJ", "LFREJ", "NOISEREJ"])
        form.addRow("Source", self.edge_source)
        form.addRow("Level", self.edge_level)
        form.addRow("Slope", self.edge_slope)
        form.addRow("Coupling", self.edge_coupling)
        note = QtWidgets.QLabel("Either-edge is not supported by the MSO2024 edge-trigger command.")
        note.setWordWrap(True)
        form.addRow(note)
        self.edge_source.currentTextChanged.connect(lambda value: self.changed.emit("set_edge_source", [value]))
        self.edge_level.valueChanged.connect(self._edge_level_changed)
        self.edge_slope.currentTextChanged.connect(lambda value: self.changed.emit("set_edge_slope", [value]))
        self.edge_coupling.currentTextChanged.connect(lambda value: self.changed.emit("set_edge_coupling", [value]))
        return page

    def _pulse_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(page)
        self.pulse_source = self._sources()
        self.pulse_polarity = QtWidgets.QComboBox()
        self.pulse_polarity.addItems(["POSITIVE", "NEGATIVE"])
        self.pulse_condition = QtWidgets.QComboBox()
        self.pulse_condition.addItems(["LESSTHAN", "MORETHAN", "EQUAL", "UNEQUAL"])
        self.pulse_time = QtWidgets.QDoubleSpinBox()
        self.pulse_time.setDecimals(9)
        self.pulse_time.setRange(1e-9, 10.0)
        self.pulse_time.setValue(1e-6)
        self.pulse_time.setSuffix(" s")
        self.pulse_time.setKeyboardTracking(False)
        apply_button = QtWidgets.QPushButton("Apply pulse parameters")
        form.addRow("Source", self.pulse_source)
        form.addRow("Polarity", self.pulse_polarity)
        form.addRow("Condition", self.pulse_condition)
        form.addRow("Width / Δt", self.pulse_time)
        form.addRow(apply_button)
        self.pulse_source.currentTextChanged.connect(self._pulse_source_changed)
        apply_button.clicked.connect(self._apply_pulse)
        return page

    def _video_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(page)
        self.video_source = self._sources()
        self.video_polarity = QtWidgets.QComboBox()
        self.video_polarity.addItems(["NEGATIVE", "POSITIVE"])
        self.video_standard = QtWidgets.QComboBox()
        self.video_standard.addItems(["NTSC", "PAL", "SECAM"])
        apply_button = QtWidgets.QPushButton("Apply video parameters")
        form.addRow("Source", self.video_source)
        form.addRow("Sync polarity", self.video_polarity)
        form.addRow("Standard", self.video_standard)
        form.addRow(apply_button)
        apply_button.clicked.connect(
            lambda: self.changed.emit(
                "set_video_trigger",
                [self.video_source.currentText(), self.video_polarity.currentText(), self.video_standard.currentText()],
            )
        )
        return page

    def _logic_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(page)
        self.logic_inputs: list[QtWidgets.QComboBox] = []
        for channel in range(1, 5):
            combo = QtWidgets.QComboBox()
            combo.addItems(["X", "HIGH", "LOW"])
            self.logic_inputs.append(combo)
            form.addRow(f"CH{channel}", combo)
        self.logic_function = QtWidgets.QComboBox()
        self.logic_function.addItems(["AND", "NAND"])
        self.logic_when = QtWidgets.QComboBox()
        self.logic_when.addItems(["TRUE", "FALSE", "LESSTHAN", "MORETHAN", "EQUAL", "UNEQUAL"])
        self.logic_time = QtWidgets.QDoubleSpinBox()
        self.logic_time.setDecimals(9)
        self.logic_time.setRange(39.6e-9, 10.0)
        self.logic_time.setValue(39.6e-9)
        self.logic_time.setSuffix(" s")
        self.logic_time.setKeyboardTracking(False)
        self.logic_clock = QtWidgets.QComboBox()
        self.logic_clock.addItems(["NONE", "CH1", "CH2", "CH3", "CH4"] + [f"D{x}" for x in range(16)])
        self.logic_clock_edge = QtWidgets.QComboBox()
        self.logic_clock_edge.addItems(["RISE", "FALL", "EITHER"])
        apply_button = QtWidgets.QPushButton("Apply logic parameters")
        form.addRow("Function", self.logic_function)
        form.addRow("When", self.logic_when)
        form.addRow("Pattern time", self.logic_time)
        form.addRow("Clock (None = pattern)", self.logic_clock)
        form.addRow("Clock edge", self.logic_clock_edge)
        form.addRow(apply_button)
        apply_button.clicked.connect(
            lambda: self.changed.emit(
                "configure_logic_trigger",
                [
                    *(combo.currentText() for combo in self.logic_inputs),
                    self.logic_function.currentText(),
                    self.logic_when.currentText(),
                    self.logic_time.value(),
                    self.logic_clock.currentText(),
                    self.logic_clock_edge.currentText(),
                ],
            )
        )
        return page

    def _setup_hold_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(page)
        sources = ["CH1", "CH2", "CH3", "CH4"] + [f"D{x}" for x in range(16)]
        self.sh_clock = QtWidgets.QComboBox()
        self.sh_clock.addItems(sources)
        self.sh_clock_edge = QtWidgets.QComboBox()
        self.sh_clock_edge.addItems(["RISE", "FALL"])
        self.sh_clock_threshold = self._voltage_spin()
        self.sh_data = QtWidgets.QComboBox()
        self.sh_data.addItems(sources)
        self.sh_data.setCurrentText("CH2")
        self.sh_data_threshold = self._voltage_spin()
        self.sh_setup_time = self._time_spin()
        self.sh_hold_time = self._time_spin(allow_negative=True)
        apply_button = QtWidgets.QPushButton("Apply setup/hold parameters")
        form.addRow("Clock source", self.sh_clock)
        form.addRow("Clock edge", self.sh_clock_edge)
        form.addRow("Clock threshold", self.sh_clock_threshold)
        form.addRow("Data source", self.sh_data)
        form.addRow("Data threshold", self.sh_data_threshold)
        form.addRow("Setup time", self.sh_setup_time)
        form.addRow("Hold time", self.sh_hold_time)
        form.addRow(apply_button)
        apply_button.clicked.connect(
            lambda: self.changed.emit(
                "configure_setup_hold_trigger",
                [
                    self.sh_clock.currentText(),
                    self.sh_clock_edge.currentText(),
                    self.sh_clock_threshold.value(),
                    self.sh_data.currentText(),
                    self.sh_data_threshold.value(),
                    self.sh_setup_time.value(),
                    self.sh_hold_time.value(),
                ],
            )
        )
        return page

    @staticmethod
    def _voltage_spin() -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setDecimals(6)
        spin.setRange(-1e6, 1e6)
        spin.setSuffix(" V")
        spin.setKeyboardTracking(False)
        return spin

    @staticmethod
    def _time_spin(allow_negative: bool = False) -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setDecimals(9)
        spin.setRange(-10.0 if allow_negative else 0.0, 10.0)
        spin.setValue(2e-9)
        spin.setSuffix(" s")
        spin.setKeyboardTracking(False)
        return spin

    def _kind_changed(self, kind: str) -> None:
        self.changed.emit("set_trigger_kind", [kind])
        if kind == "Edge":
            self.stack.setCurrentWidget(self.edge_page)
        elif kind in {"Pulse Width", "Runt", "Rise/Fall Time"}:
            self.stack.setCurrentWidget(self.pulse_page)
            has_occurs = self.pulse_condition.findText("OCCURS") >= 0
            if kind == "Runt" and not has_occurs:
                self.pulse_condition.addItem("OCCURS")
            elif kind != "Runt" and has_occurs:
                self.pulse_condition.removeItem(self.pulse_condition.findText("OCCURS"))
            blocker = QtCore.QSignalBlocker(self.pulse_condition)
            self.pulse_condition.clear()
            if kind == "Rise/Fall Time":
                self.pulse_condition.addItems(["SLOWER", "FASTER", "EQUAL", "UNEQUAL"])
            else:
                self.pulse_condition.addItems(["LESSTHAN", "MORETHAN", "EQUAL", "UNEQUAL"])
                if kind == "Runt":
                    self.pulse_condition.addItem("OCCURS")
            del blocker
            blocker = QtCore.QSignalBlocker(self.pulse_polarity)
            self.pulse_polarity.clear()
            self.pulse_polarity.addItems(["POSITIVE", "NEGATIVE"])
            if kind in {"Runt", "Rise/Fall Time"}:
                self.pulse_polarity.addItem("EITHER")
            del blocker
        elif kind == "Video":
            self.stack.setCurrentWidget(self.video_page)
        elif kind == "Logic":
            self.stack.setCurrentWidget(self.logic_page)
        elif kind == "Setup/Hold":
            self.stack.setCurrentWidget(self.setup_hold_page)
        else:
            self.stack.setCurrentWidget(self.info_page)
            messages = {
                "Serial Bus (option)": "Serial bus trigger requires DPO2AUTO or DPO2EMBD and a configured B1/B2 bus. The instrument will report an event if the option is absent.",
            }
            self.info_page.setText(messages.get(kind, ""))

    def _edge_level_changed(self, value: float) -> None:
        source = self.edge_source.currentText()
        if source.startswith("CH"):
            self.changed.emit("set_trigger_level", [int(source[-1]), value])

    def _pulse_source_changed(self, source: str) -> None:
        self.changed.emit("set_pulse_source", [self.kind.currentText(), source])

    def _apply_pulse(self) -> None:
        self.changed.emit(
            "set_pulse_parameter",
            [self.kind.currentText(), self.pulse_polarity.currentText(), self.pulse_condition.currentText(), self.pulse_time.value()],
        )

    def apply_state(self, state: dict) -> None:
        for widget, value in ((self.kind, state.get("kind", "Edge")), (self.mode, state.get("mode", "AUTO"))):
            blocker = QtCore.QSignalBlocker(widget)
            widget.setCurrentText(value)
            del blocker
        blocker = QtCore.QSignalBlocker(self.holdoff)
        self.holdoff.setValue(float(state.get("holdoff", 20e-9)))
        del blocker
        if state.get("kind") == "Edge":
            for widget, value in (
                (self.edge_source, state.get("source", "CH1")),
                (self.edge_slope, state.get("slope", "RISE")),
                (self.edge_coupling, state.get("coupling", "DC")),
            ):
                blocker = QtCore.QSignalBlocker(widget)
                widget.setCurrentText(value)
                del blocker
            if "level" in state:
                blocker = QtCore.QSignalBlocker(self.edge_level)
                self.edge_level.setValue(float(state["level"]))
                del blocker
        self._kind_changed_without_signal(state.get("kind", "Edge"))

    def _kind_changed_without_signal(self, kind: str) -> None:
        if kind == "Edge":
            self.stack.setCurrentWidget(self.edge_page)
        elif kind in {"Pulse Width", "Runt", "Rise/Fall Time"}:
            self.stack.setCurrentWidget(self.pulse_page)
        elif kind == "Video":
            self.stack.setCurrentWidget(self.video_page)
        elif kind == "Logic":
            self.stack.setCurrentWidget(self.logic_page)
        elif kind == "Setup/Hold":
            self.stack.setCurrentWidget(self.setup_hold_page)
        else:
            self.stack.setCurrentWidget(self.info_page)
