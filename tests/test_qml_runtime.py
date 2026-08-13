import os
import subprocess
import sys
import textwrap
from pathlib import Path


def test_qml_loads_without_warnings_and_switches_compact_layout():
    project_root = Path(__file__).resolve().parents[1]
    script = textwrap.dedent(
        """
        from pathlib import Path
        from PySide6 import QtCore, QtGui, QtQuick, QtQml, QtTest
        from mso2024_remote.qml_bridge import ScopeController

        app = QtGui.QGuiApplication([])
        engine = QtQml.QQmlApplicationEngine()
        warnings = []
        engine.warnings.connect(
            lambda values: warnings.extend(value.toString() for value in values)
        )
        scope = ScopeController(simulation=True)
        engine.rootContext().setContextProperty("scope", scope)
        qml_path = Path("mso2024_remote/qml/Main.qml").resolve()
        engine.load(QtCore.QUrl.fromLocalFile(str(qml_path)))
        assert len(engine.rootObjects()) == 1

        root = engine.rootObjects()[0]
        root.setWidth(1080)
        root.setHeight(680)
        app.processEvents()
        assert root.property("compactLayout") is True
        assert root.property("frontPanelMode") is False

        root.setWidth(1500)
        root.setHeight(920)
        app.processEvents()
        assert root.property("compactLayout") is False
        assert root.property("frontPanelMode") is True

        def visual_item(name):
            pending = [root.contentItem()]
            while pending:
                item = pending.pop()
                if item.objectName() == name:
                    return item
                pending.extend(item.childItems())
            raise AssertionError(f"QML item not found: {name}")

        def drag_up(item, local_position=None, modifiers=QtCore.Qt.NoModifier):
            local_position = local_position or QtCore.QPointF(item.width() / 2, 45)
            start = item.mapToScene(local_position)
            end = QtCore.QPointF(start.x(), start.y() - 14)
            events = (
                QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, start, start, start, QtCore.Qt.LeftButton, QtCore.Qt.LeftButton, modifiers),
                QtGui.QMouseEvent(QtCore.QEvent.MouseMove, end, end, end, QtCore.Qt.NoButton, QtCore.Qt.LeftButton, modifiers),
                QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, end, end, end, QtCore.Qt.LeftButton, QtCore.Qt.NoButton, modifiers),
            )
            for event in events:
                QtCore.QCoreApplication.sendEvent(root, event)
                app.processEvents()

        def click(item, local_position=None):
            local_position = local_position or QtCore.QPointF(item.width() / 2, item.height() / 2)
            position = item.mapToScene(local_position)
            for event in (
                QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, position, position, position, QtCore.Qt.LeftButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier),
                QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, position, position, position, QtCore.Qt.LeftButton, QtCore.Qt.NoButton, QtCore.Qt.NoModifier),
            ):
                QtCore.QCoreApplication.sendEvent(root, event)
                app.processEvents()

        def drag_horizontal(item, start_fraction, end_fraction):
            start = item.mapToScene(QtCore.QPointF(item.width() * start_fraction, item.height() / 2))
            end = item.mapToScene(QtCore.QPointF(item.width() * end_fraction, item.height() / 2))
            for event in (
                QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, start, start, start, QtCore.Qt.LeftButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier),
                QtGui.QMouseEvent(QtCore.QEvent.MouseMove, end, end, end, QtCore.Qt.NoButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier),
                QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, end, end, end, QtCore.Qt.LeftButton, QtCore.Qt.NoButton, QtCore.Qt.NoModifier),
            ):
                QtCore.QCoreApplication.sendEvent(root, event)
                app.processEvents()

        channel_position = visual_item("channelPositionKnob1")
        drag_up(channel_position)
        assert scope.channelPosition(1) == 0.1
        assert channel_position.property("valueText") == "0.1 div"
        channel_scale = visual_item("channelScaleKnob1")
        drag_up(channel_scale)
        assert scope.channelScale(1) == 0.2
        assert channel_scale.property("valueText") == "200 mV/div"
        drag_up(visual_item("horizontalScaleKnob"))
        assert scope.timeScale == 0.0005
        horizontal_position = visual_item("horizontalPositionKnob")
        drag_up(horizontal_position)
        assert scope.horizontalPosition == 51.0
        assert horizontal_position.property("valueText") == "51.0 %"
        drag_up(horizontal_position, modifiers=QtCore.Qt.ShiftModifier)
        assert scope.horizontalPosition == 51.2
        trigger_knob = visual_item("triggerLevelKnob")
        drag_up(trigger_knob)
        assert scope.triggerLevel == 0.05
        click(trigger_knob)
        assert scope.triggerLevel == 0.0
        multipurpose_a = visual_item("multipurposeAKnob")
        drag_up(multipurpose_a)
        assert scope.knobAValue == "AC"
        assert scope.bottomMenu[0]["value"] == "DC"
        click(multipurpose_a)
        assert scope.bottomMenu[0]["value"] == "AC"

        scope.openMenu("acquire")
        scope.selectMenuItem(2)
        scope.selectSideItem(1)
        app.processEvents()
        assert scope.delayMode
        assert horizontal_position.property("label") == "DELAY"
        drag_up(horizontal_position)
        assert scope.horizontalDelay == 0.00005
        drag_up(horizontal_position, modifiers=QtCore.Qt.ShiftModifier)
        assert scope.horizontalDelay == 0.00006
        assert scope.bottomMenu[2]["value"] == "On"
        assert scope.bottomMenu[3]["value"] == "60 us"

        run_stop = visual_item("runStopButton")
        click(run_stop)
        assert not scope.running
        assert run_stop.property("text") == "STOPPED"
        click(run_stop)
        assert scope.running

        click(visual_item("frontChannelButton2"))
        assert scope.selectedChannel == 2
        assert scope.channelEnabledStates[1]
        assert scope.menuContext == "channel"
        click(visual_item("bottomSoftKey4"))
        channel_label_dialog = root.findChild(QtCore.QObject, "channelLabelDialog")
        channel_label_field = root.findChild(QtCore.QObject, "channelLabelField")
        assert channel_label_dialog is not None and channel_label_dialog.property("visible")
        assert channel_label_field is not None
        channel_label_field.setProperty("text", "CLOCK INPUT")
        assert QtCore.QMetaObject.invokeMethod(channel_label_dialog, "accept")
        app.processEvents()
        assert scope.channelLabels[1] == "CLOCK INPUT"
        assert scope.bottomMenu[4]["value"] == "CLOCK INPUT"

        click(visual_item("measureButton"))
        assert scope.menuContext == "measure"
        click(visual_item("bottomSoftKey0"))
        assert scope.sideMenuVisible
        source_button = visual_item("measurementSource1Channel3")
        assert source_button.isVisible() and source_button.isEnabled()
        click(source_button)
        assert scope.measurementSource == "CH3"
        click(visual_item("sideSoftKey0"))
        assert scope.measurementReadouts[0]["type"] == "Amplitude"
        assert scope.measurementReadouts[0]["source"] == "CH3"

        trigger_marker = visual_item("triggerMarker")
        marker_y = trigger_marker.y()
        drag_up(trigger_marker, QtCore.QPointF(9, 9))
        assert scope.triggerLevel > 0.0
        assert trigger_marker.y() < marker_y

        inspector = visual_item("waveInspectorKnob")
        drag_up(inspector, QtCore.QPointF(12, 61))
        assert scope.zoomPosition == 52.0
        drag_up(inspector, QtCore.QPointF(46, 61))
        assert scope.zoomScale == 0.0004
        zoom_overview = visual_item("zoomOverview")
        assert zoom_overview.isVisible()
        drag_horizontal(zoom_overview, 0.25, 0.75)
        assert abs(scope.zoomPosition - 75.0) < 1e-6

        display = visual_item("scopeDisplay")
        drag_up(display, QtCore.QPointF(display.width() / 2, display.height() / 2))
        assert scope.channelPosition(1) == 0.1
        assert scope.channelPosition(2) == 0.1
        assert channel_position.property("valueText") == "0.1 div"
        assert visual_item("channelPositionKnob2").property("valueText") == "0.1 div"

        mode_toggle = visual_item("modeToggleButton")
        click(mode_toggle)
        assert root.property("enhancedMode") is True
        assert root.property("frontPanelMode") is False
        click(mode_toggle)
        assert root.property("enhancedMode") is False
        assert root.property("frontPanelMode") is True

        root.requestActivate()
        app.processEvents()
        QtTest.QTest.keyClick(root, QtCore.Qt.Key_M)
        app.processEvents()
        assert scope.menuContext == "measure"
        QtTest.QTest.keyClick(root, QtCore.Qt.Key_Escape)
        app.processEvents()
        assert scope.menuContext == ""

        QtTest.QTest.keyClick(root, QtCore.Qt.Key_F11)
        app.processEvents()
        assert root.visibility() == QtGui.QWindow.FullScreen
        QtTest.QTest.keyClick(root, QtCore.Qt.Key_F11)
        app.processEvents()
        assert root.visibility() != QtGui.QWindow.FullScreen

        context_menu = root.findChild(QtCore.QObject, "waveformContextMenu")
        assert context_menu is not None
        assert context_menu.property("height") >= 220

        scope._simulation = False
        scope._connection_changed(False, "", "")
        app.processEvents()
        connection_overlay = root.findChild(QtCore.QObject, "connectionOverlay")
        assert connection_overlay is not None
        assert connection_overlay.property("visible") is True
        assert connection_overlay.property("width") == root.width()
        assert connection_overlay.property("height") == root.height()
        assert not warnings, "\\n".join(warnings)
        scope.close()
        """
    )
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
