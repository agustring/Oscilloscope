from __future__ import annotations

from PySide6 import QtCore, QtGui
import pyqtgraph as pg


CHANNEL_COLORS = {1: "#ffd21f", 2: "#4ddc75", 3: "#55aaff", 4: "#d96cff"}


class ScopeViewBox(pg.ViewBox):
    horizontal_pan = QtCore.Signal(float)
    reset_requested = QtCore.Signal()

    def mouseDragEvent(self, event, axis=None):
        super().mouseDragEvent(event, axis=axis)
        if event.isFinish():
            low, high = self.viewRange()[0]
            self.horizontal_pan.emit((low + high) / 2.0)

    def mouseDoubleClickEvent(self, event):
        self.reset_requested.emit()
        event.accept()


class WaveformView(pg.PlotWidget):
    vertical_zoom = QtCore.Signal(int, int)
    horizontal_zoom = QtCore.Signal(int)
    horizontal_pan = QtCore.Signal(float)
    reset_requested = QtCore.Signal(int)
    cursor_moved = QtCore.Signal(str, int, float)

    def __init__(self, parent=None):
        self.view_box = ScopeViewBox()
        super().__init__(parent=parent, viewBox=self.view_box)
        self.selected_channel = 1
        self.curves: dict[int, pg.PlotDataItem] = {}
        self._updating_cursors = False
        self.cursor_lines: dict[str, pg.InfiniteLine] = {}

        self.setBackground("#081016")
        self.showGrid(x=True, y=True, alpha=0.28)
        self.setLabel("bottom", "Time", units="s")
        self.setLabel("left", "Voltage", units="V")
        self.getPlotItem().setTitle("LIVE WAVEFORMS", color="#b8c8d8", size="11pt")
        self.setMouseEnabled(x=True, y=False)
        self.view_box.setMenuEnabled(False)
        self.view_box.horizontal_pan.connect(self.horizontal_pan)
        self.view_box.reset_requested.connect(lambda: self.reset_requested.emit(self.selected_channel))
        for channel, color in CHANNEL_COLORS.items():
            curve = self.plot([], [], pen=pg.mkPen(color, width=1.35), name=f"CH{channel}")
            curve.setCurveClickable(True, width=8)
            curve.sigClicked.connect(lambda _curve, _event=None, ch=channel: self.select_channel(ch))
            self.curves[channel] = curve
        self.addLegend(offset=(10, 10))

    def select_channel(self, channel: int) -> None:
        self.selected_channel = channel
        for number, curve in self.curves.items():
            width = 2.2 if number == channel else 1.2
            curve.setPen(pg.mkPen(CHANNEL_COLORS[number], width=width))

    @QtCore.Slot(int, object, object, object)
    def update_waveform(self, channel: int, time, voltage, _preamble) -> None:
        self.curves[channel].setData(time, voltage, connect="finite")
        if len(time):
            self.setXRange(float(time[0]), float(time[-1]), padding=0.01)

    def set_channel_visible(self, channel: int, visible: bool) -> None:
        self.curves[channel].setVisible(visible)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        direction = 1 if event.angleDelta().y() > 0 else -1
        if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            self.horizontal_zoom.emit(direction)
        else:
            self.vertical_zoom.emit(self.selected_channel, direction)
        event.accept()

    def set_cursor_state(self, state: dict) -> None:
        function = state.get("function", "OFF")
        wanted: dict[str, tuple[float, int, str]] = {}
        if function in {"VBARS", "SCREEN"}:
            wanted.update(x1=(state.get("x1", 0.0), 90, "VBARS"), x2=(state.get("x2", 0.0), 90, "VBARS"))
        if function in {"HBARS", "SCREEN"}:
            wanted.update(y1=(state.get("y1", 0.0), 0, "HBARS"), y2=(state.get("y2", 0.0), 0, "HBARS"))
        for name in list(self.cursor_lines):
            if name not in wanted:
                self.removeItem(self.cursor_lines.pop(name))
        self._updating_cursors = True
        try:
            for name, (position, angle, axis) in wanted.items():
                line = self.cursor_lines.get(name)
                if line is None:
                    line = pg.InfiniteLine(
                        angle=angle,
                        movable=True,
                        pen=pg.mkPen("#ff8d32", width=1.4),
                        hoverPen=pg.mkPen("#ffffff", width=2),
                        label=name.upper(),
                    )
                    cursor_number = int(name[-1])
                    line.sigPositionChangeFinished.connect(
                        lambda item, ax=axis, number=cursor_number: self._cursor_finished(ax, number, item)
                    )
                    self.addItem(line)
                    self.cursor_lines[name] = line
                line.setValue(float(position))
        finally:
            self._updating_cursors = False

    def _cursor_finished(self, axis: str, number: int, line: pg.InfiniteLine) -> None:
        if not self._updating_cursors:
            self.cursor_moved.emit(axis, number, float(line.value()))
