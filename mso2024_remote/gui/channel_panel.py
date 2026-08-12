from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from .waveform_view import CHANNEL_COLORS


class ChannelPanel(QtWidgets.QWidget):
    changed = QtCore.Signal(str, object)
    selected = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.controls: dict[int, dict[str, QtWidgets.QWidget]] = {}
        tabs = QtWidgets.QTabWidget()
        for channel in range(1, 5):
            tabs.addTab(self._channel_tab(channel), f"CH{channel}")
            tabs.tabBar().setTabTextColor(channel - 1, CHANNEL_COLORS[channel])
        tabs.currentChanged.connect(lambda index: self.selected.emit(index + 1))
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(tabs)

    def _channel_tab(self, channel: int) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(page)
        enabled = QtWidgets.QCheckBox("Display waveform")
        scale = QtWidgets.QDoubleSpinBox()
        scale.setDecimals(6)
        scale.setRange(1e-6, 1e6)
        scale.setValue(1.0)
        scale.setSuffix(" V/div")
        scale.setKeyboardTracking(False)
        position = QtWidgets.QDoubleSpinBox()
        position.setRange(-4.0, 4.0)
        position.setSingleStep(0.1)
        position.setSuffix(" div")
        position.setKeyboardTracking(False)
        coupling = QtWidgets.QComboBox()
        coupling.addItems(["DC", "AC", "GND"])
        attenuation = QtWidgets.QComboBox()
        attenuation.addItems(["1", "10", "100", "1000"])
        bandwidth = QtWidgets.QComboBox()
        bandwidth.addItems(["Full", "20 MHz"])
        invert = QtWidgets.QCheckBox("Invert display")
        label = QtWidgets.QLineEdit()
        label.setMaxLength(30)
        label.setPlaceholderText("up to 30 characters")
        self.controls[channel] = {
            "enabled": enabled,
            "scale": scale,
            "position": position,
            "coupling": coupling,
            "attenuation": attenuation,
            "bandwidth": bandwidth,
            "invert": invert,
            "label": label,
        }
        form.addRow(enabled)
        form.addRow("Scale", scale)
        form.addRow("Position", position)
        form.addRow("Coupling", coupling)
        form.addRow("Probe ×", attenuation)
        form.addRow("Bandwidth", bandwidth)
        form.addRow(invert)
        form.addRow("Label", label)
        enabled.toggled.connect(lambda value: self.changed.emit("set_channel_enabled", [channel, value]))
        scale.valueChanged.connect(lambda value: self.changed.emit("set_vertical_scale", [channel, value]))
        position.valueChanged.connect(lambda value: self.changed.emit("set_vertical_position", [channel, value]))
        coupling.currentTextChanged.connect(lambda value: self.changed.emit("set_coupling", [channel, value]))
        attenuation.currentTextChanged.connect(lambda value: self.changed.emit("set_probe_attenuation", [channel, float(value)]))
        bandwidth.currentTextChanged.connect(lambda value: self.changed.emit("set_bandwidth", [channel, value]))
        invert.toggled.connect(lambda value: self.changed.emit("set_invert", [channel, value]))
        label.editingFinished.connect(lambda: self.changed.emit("set_channel_label", [channel, label.text()]))
        return page

    def apply_state(self, states: dict) -> None:
        for channel, state in states.items():
            widgets = self.controls[int(channel)]
            values = {
                "enabled": bool(state.get("enabled", False)),
                "scale": float(state.get("scale", 1.0)),
                "position": float(state.get("position", 0.0)),
                "coupling": state.get("coupling", "DC"),
                "attenuation": f"{float(state.get('attenuation', 1)):g}",
                "bandwidth": "20 MHz" if "20" in str(state.get("bandwidth", "")) else "Full",
                "invert": bool(state.get("invert", False)),
                "label": state.get("label", ""),
            }
            for name, widget in widgets.items():
                blocker = QtCore.QSignalBlocker(widget)
                value = values[name]
                if isinstance(widget, QtWidgets.QCheckBox):
                    widget.setChecked(value)
                elif isinstance(widget, QtWidgets.QDoubleSpinBox):
                    widget.setValue(value)
                elif isinstance(widget, QtWidgets.QComboBox):
                    widget.setCurrentText(value)
                elif isinstance(widget, QtWidgets.QLineEdit):
                    widget.setText(value)
                del blocker
