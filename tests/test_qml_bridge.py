import io

from PySide6 import QtCore

from mso2024_remote.instrument.mso2024 import MEASUREMENT_TYPES
from mso2024_remote.qml_bridge import MEASUREMENT_CHOICES, ScopeController, TIME_STEPS, VERTICAL_STEPS, _step


def controller():
    if QtCore.QCoreApplication.instance() is None:
        QtCore.QCoreApplication([])
    return ScopeController(simulation=True)


def test_vertical_detents_follow_125_sequence():
    assert min(VERTICAL_STEPS) == 0.002
    assert max(VERTICAL_STEPS) == 5.0
    assert _step(VERTICAL_STEPS, 0.5, 1) == 0.2
    assert _step(VERTICAL_STEPS, 0.5, -1) == 1.0


def test_timebase_detents_respect_mso2024_range():
    assert min(TIME_STEPS) == 2e-9
    assert max(TIME_STEPS) == 100.0
    assert _step(TIME_STEPS, 1e-3, 1) == 5e-4


def test_horizontal_position_knob_respects_delay_mode_and_updates_acquire_menu():
    scope = controller()
    calls = []
    scope._queue = lambda key, method, args: calls.append((key, method, args))
    scope.openMenu("acquire")

    scope.adjustHorizontalPosition(0.1)
    assert scope.horizontalPosition == 51.0
    assert calls[-1] == ("horizontal_position", "set_horizontal_position", [51.0])
    assert scope.bottomMenu[2]["value"] == "Off"
    assert scope.bottomMenu[3]["value"] == "51 %"

    scope.selectMenuItem(2)
    scope.selectSideItem(1)
    scope.adjustHorizontalPosition(0.1)
    assert scope.delayMode
    assert scope.horizontalDelay == 0.0001
    assert calls[-1] == ("horizontal_delay", "set_delay", [0.0001])
    assert scope.bottomMenu[2]["value"] == "On"
    assert scope.bottomMenu[3]["value"] == "100 us"
    scope.close()


def test_simulation_single_acquires_one_frame_and_autoset_restores_view():
    scope = controller()
    scope._simulate_frame()
    phase = scope._phase

    scope.single()
    assert not scope.running
    assert scope._phase > phase
    stopped_phase = scope._phase
    scope._simulate_frame()
    assert scope._phase == stopped_phase

    scope.adjustChannelScale(1, 1)
    scope.adjustChannelPosition(1, 1)
    scope.adjustTimeScale(1)
    scope.adjustHorizontalPosition(0.1)
    scope.adjustTriggerLevel(1)
    scope.autoset()
    assert scope.running
    assert scope.channelScale(1) == 0.5
    assert scope.channelPosition(1) == 0.0
    assert scope.timeScale == 1e-3
    assert scope.horizontalPosition == 50.0
    assert not scope.delayMode
    assert scope.triggerLevel == 0.0
    scope.close()


def test_display_waveform_is_bounded_without_losing_raw_point_diagnostics():
    scope = controller()
    values = list(range(5000))
    scope._waveform(1, values, values, {})
    assert len(scope.waveforms[0]) <= 1250
    assert scope.waveformPointCount == 5000
    assert "GUI State: RUN · CH1 · channel" in scope.diagnosticsText
    scope.close()


def test_wave_inspector_playback_updates_simulated_pan_position():
    scope = controller()
    initial_position = scope.zoomPosition
    scope.toggleInspectorPlayback()
    scope._simulate_frame()
    assert scope.inspectorPlaying
    assert scope.zoomEnabled
    assert scope.zoomPosition > initial_position
    scope.close()


def test_wave_inspector_readback_and_fine_adjustments_update_state():
    scope = controller()
    scope._snapshot({"zoom": {"enabled": True, "scale": 0.02, "position": 40.0}})
    assert scope.zoomEnabled
    assert scope.zoomScale == 0.02
    assert scope.zoomPosition == 40.0

    scope.panZoom(1, True)
    assert scope.zoomPosition == 40.5
    scope.adjustZoom(1, True)
    assert scope.zoomScale == 0.019
    scope.close()


def test_trigger_status_uses_hardware_snapshot_state():
    scope = controller()
    scope._snapshot({"trigger": {"status": "READY", "source": "CH2", "level": 0.75}})

    assert scope.triggerStatus == "READY"
    assert scope.triggerSource == "CH2"
    assert scope.triggerLevel == 0.75
    scope.close()


def test_trigger_level_adjustment_and_center_queue_physical_updates():
    scope = controller()
    calls = []
    scope._queue = lambda key, method, args: calls.append((key, method, args))

    scope.selectChannel(3)
    calls.clear()
    scope.adjustTriggerLevel(1)
    scope.centerTrigger()

    assert calls == [
        ("trigger", "set_trigger_level", [3, 0.05]),
        ("trigger", "set_trigger_level", [3, 0.0]),
    ]
    scope.close()


def test_wave_inspector_set_clear_queues_physical_toggle():
    scope = controller()
    calls = []
    scope._queue = lambda key, method, args: calls.append((key, method, args))

    scope.toggleMark()

    assert calls == [("mark_toggle", "toggle_mark", [])]
    scope.close()


def test_test_button_opens_option_dependent_menu_and_queues_front_panel_press():
    scope = controller()
    calls = []
    scope._queue = lambda key, method, args: calls.append((key, method, args))
    scope.openTestMenu()
    assert scope.menuContext == "test"
    assert scope.bottomMenu[0] == {"title": "Application Test", "value": "Option dependent"}
    assert calls[-1][1:] == ("open_test_menu", [])
    scope.close()


def test_panel_capture_uses_window_screen_and_reports_completion():
    class Pixmap:
        def isNull(self): return False
        def save(self, path, file_format):
            assert path == "panel.png"
            assert file_format == "PNG"
            return True

    class Screen:
        def grabWindow(self, window_id):
            assert window_id == 42
            return Pixmap()

    class Window:
        def screen(self): return Screen()
        def winId(self): return 42

    scope = controller()
    scope.savePanelImage("panel.png", Window())
    assert scope._last_rx == "screen_saved: panel.png"
    scope.close()


def test_trigger_side_menu_updates_central_state():
    scope = controller()
    scope.openMenu("trigger")
    scope.selectMenuItem(3)
    assert [item["label"] for item in scope.sideMenu] == ["Rising", "Falling"]
    scope.selectSideItem(1)
    assert scope.bottomMenu[3]["value"] == "Falling"
    scope.close()


def test_pulse_trigger_menu_queues_family_specific_commands():
    scope = controller()
    calls = []
    scope._queue = lambda key, method, args: calls.append((key, method, args))
    scope.openMenu("trigger")
    scope.selectSideItem(1)  # Pulse Width
    assert [item["title"] for item in scope.bottomMenu] == [
        "Type", "Source", "Polarity", "Trigger When", "Width", "Mode/Holdoff"
    ]
    scope.selectMenuItem(3)
    scope.selectSideItem(1)  # More Than
    assert calls[-1][1:] == (
        "set_pulse_parameter", ["Pulse Width", "POSITIVE", "MORETHAN", 1e-6]
    )
    scope.selectMenuItem(4)
    scope.selectSideItem(1)  # 50 ns
    assert scope.bottomMenu[4]["value"] == "50 ns"
    assert calls[-1][2][-1] == 50e-9
    scope.close()


def test_logic_setup_hold_and_video_menus_queue_valid_presets():
    scope = controller()
    calls = []
    scope._queue = lambda key, method, args: calls.append((key, method, args))
    scope.openMenu("trigger")

    scope.selectSideItem(3)  # Logic
    scope.selectMenuItem(1)
    scope.selectSideItem(1)  # L H X X
    assert calls[-1][1] == "configure_logic_trigger"
    assert calls[-1][2][:4] == ["LOW", "HIGH", "X", "X"]

    scope.selectMenuItem(0)
    scope.selectSideItem(4)  # Setup/Hold
    scope.selectMenuItem(1)
    scope.selectSideItem(1)  # CH3; CH2 is excluded because it is data
    assert calls[-1][1] == "configure_setup_hold_trigger"
    assert calls[-1][2][0] == "CH3"
    assert calls[-1][2][3] == "CH2"

    scope.selectMenuItem(0)
    scope.selectSideItem(6)  # Video
    scope.selectMenuItem(3)
    scope.selectSideItem(1)  # PAL
    assert calls[-1][1:] == ("set_video_trigger", ["CH1", "POSITIVE", "PAL"])
    scope.close()


def test_logic_menu_queues_digital_pattern_and_full_threshold_range():
    scope = controller()
    calls = []
    scope._queue = lambda key, method, args: calls.append((key, method, args))
    scope.openMenu("trigger")
    scope.selectSideItem(3)  # Logic

    scope.selectMenuItem(2)
    scope.selectSideItem(0)  # D0:H D1:L
    assert calls[-1][1] == "configure_logic_trigger"
    assert calls[-1][2][8] == "RISE"
    assert calls[-1][2][9] == ("HIGH", "LOW", "X", "X")

    scope.selectMenuItem(5)
    labels = [item["label"] for item in scope.sideMenu]
    scope.selectSideItem(labels.index("D15 -1.3 V"))
    assert calls[-1][2][10:] == ["D15", -1.3]
    assert scope.bottomMenu[5]["value"] == "D15 -1.3 V"
    scope.close()


def test_setup_hold_trigger_exposes_digital_sources_and_thresholds():
    scope = controller()
    calls = []
    scope._queue = lambda key, method, args: calls.append((key, method, args))
    scope.openMenu("trigger")
    scope.selectSideItem(4)  # Setup/Hold

    scope.selectMenuItem(1)
    labels = [item["label"] for item in scope.sideMenu]
    scope.selectSideItem(labels.index("D15 -1.3 V"))
    assert calls[-1][1] == "configure_setup_hold_trigger"
    assert calls[-1][2][:3] == ["D15", "RISE", -1.3]

    scope.selectMenuItem(3)
    labels = [item["label"] for item in scope.sideMenu]
    scope.selectSideItem(labels.index("D14 1.4 V"))
    assert calls[-1][2][3:5] == ["D14", 1.4]
    assert scope.bottomMenu[1]["value"] == "D15 -1.3 V"
    assert scope.bottomMenu[3]["value"] == "D14 1.4 V"
    scope.close()


def test_search_type_menu_excludes_video_and_updates_state():
    scope = controller()
    calls = []
    scope._queue = lambda key, method, args: calls.append((key, method, args))
    scope.openMenu("search")
    scope.selectMenuItem(1)
    labels = [item["label"] for item in scope.sideMenu]
    assert "Video" not in labels
    scope.selectSideItem(labels.index("Runt"))
    assert scope.bottomMenu[1]["value"] == "Runt"
    assert calls[-1][1:] == ("set_search_kind", ["Runt"])
    scope.close()


def test_search_edge_and_pulse_menus_queue_dedicated_criteria():
    scope = controller()
    calls = []
    scope._queue = lambda key, method, args: calls.append((key, method, args))
    scope.openMenu("search")
    assert [item["title"] for item in scope.bottomMenu] == ["Search", "Type", "Source", "Slope", "Level", "Actions"]
    scope.selectMenuItem(2)
    scope.selectSideItem(1)
    assert calls[-1][1:] == ("configure_edge_search", ["CH2", "RISE", 0.0])

    scope.selectMenuItem(1)
    scope.selectSideItem(1)  # Pulse Width
    assert [item["title"] for item in scope.bottomMenu] == ["Search", "Type", "Source", "Polarity", "When", "Width", "Actions"]
    scope.selectMenuItem(4)
    scope.selectSideItem(1)  # More Than
    assert calls[-1][1:] == ("configure_pulse_search", ["Pulse Width", "CH2", "POSITIVE", "MORETHAN", 1e-6])
    scope.selectMenuItem(6)
    scope.selectSideItem(0)
    assert calls[-1][1:] == ("copy_search_settings", [True])
    scope.close()


def test_search_logic_and_setup_hold_use_their_own_state():
    scope = controller()
    calls = []
    scope._queue = lambda key, method, args: calls.append((key, method, args))
    scope.openMenu("search")
    scope.selectMenuItem(1)
    scope.selectSideItem(3)  # Logic
    scope.selectMenuItem(2)
    scope.selectSideItem(1)
    assert calls[-1][1] == "configure_logic_search"
    assert calls[-1][2][:4] == ["LOW", "HIGH", "X", "X"]

    scope.selectMenuItem(1)
    scope.selectSideItem(4)  # Setup/Hold
    scope.selectMenuItem(4)
    labels = [item["label"] for item in scope.sideMenu]
    scope.selectSideItem(labels.index("D0"))
    assert calls[-1][1] == "configure_setup_hold_search"
    assert calls[-1][2][0] == "CH1"
    assert calls[-1][2][3] == "D0"
    scope.close()


def test_measurement_knobs_choose_type_and_source():
    scope = controller()
    scope.openMenu("measure")
    scope.selectMenuItem(0)
    scope.adjustMultipurpose("B", 1)
    scope.selectSideItem(MEASUREMENT_CHOICES.index("Frequency"))
    assert scope.measurementReadouts[0]["type"] == "Frequency"
    assert scope.measurementReadouts[0]["source"] == "CH2"
    scope.close()


def test_measurement_menu_exposes_every_single_source_measurement():
    assert set(MEASUREMENT_CHOICES) == set(MEASUREMENT_TYPES)


def test_delay_measurement_uses_ordered_source_pair_from_knob_b():
    scope = controller()
    calls = []
    scope._queue = lambda key, method, args: calls.append((key, method, args))
    scope.openMenu("measure")
    scope.selectMenuItem(0)
    scope._side_selection = MEASUREMENT_CHOICES.index("Delay")
    assert scope.knobBLabel == "Sources"
    assert scope.knobBValue == "CH1 → CH2"
    scope.adjustMultipurpose("B", 1)
    assert scope.knobBValue == "CH1 → CH3"
    scope.applyMultipurpose()
    assert calls[-1][1:] == ("configure_measurement", [1, "DELAY", "CH1", True, "CH3"])
    scope.close()


def test_save_menu_requests_pc_file_workflows():
    scope = controller()
    requests = []
    scope.fileDialogRequested.connect(requests.append)
    scope.openMenu("save")
    scope.pressMenuItem(0)
    scope.pressMenuItem(1)
    scope.pressMenuItem(3)
    assert requests == ["screen-save", "waveform-save", "waveform-load"]
    scope.close()


def test_simulated_waveform_can_round_trip_through_csv(monkeypatch):
    class MemoryFile(io.StringIO):
        def close(self): pass

    contents = MemoryFile()
    monkeypatch.setattr("builtins.open", lambda *_args, **_kwargs: contents)
    scope = controller()
    scope._simulate_frame()
    scope.exportWaveform("channel.csv")
    assert contents.getvalue().startswith("time_s,voltage_V")
    contents.seek(0)
    scope.loadReferenceWaveform("channel.csv")
    assert len(scope.referenceWaveform) == 900
    assert "waveform_loaded" in scope.diagnosticsText
    scope.close()


def test_measurement_gating_method_and_indicators_are_functional():
    scope = controller()
    calls = []
    scope._queue = lambda key, method, args: calls.append((key, method, args))
    scope.openMenu("measure")
    scope.selectMenuItem(0)
    scope.selectSideItem(MEASUREMENT_CHOICES.index("Frequency"))
    scope.selectMenuItem(2)
    scope.selectSideItem(1)
    assert calls[-1][1:] == ("set_measurement_indicators", [1])
    scope.selectMenuItem(3)
    scope.selectSideItem(2)
    assert calls[-1][1:] == ("set_measurement_gating", ["CURSOR"])
    scope.selectMenuItem(4)
    scope.selectSideItem(2)
    assert calls[-1][1:] == ("set_measurement_method", ["MINMAX"])
    scope.close()


def test_waveform_cursor_link_and_bring_on_screen_are_functional():
    scope = controller()
    calls = []
    scope._queue = lambda key, method, args: calls.append((key, method, args))
    scope._cursors_ready({
        "function": "WAVEFORM", "mode": "INDEPENDENT",
        "x1": -0.001, "x2": 0.001, "vdelta": 1.5,
    })
    scope.openMenu("cursor")
    assert scope.sideMenu[4]["selected"]
    assert scope.knobAValue == "Waveform"

    scope.selectMenuItem(2)
    scope.selectSideItem(1)
    assert scope.bottomMenu[2]["value"] == "Track"
    assert calls[-1][1:] == ("set_cursor_mode", ["TRACK"])

    scope.pressMenuItem(1)
    assert scope.cursorX1 == -2.0 * scope.timeScale
    assert scope.cursorX2 == 2.0 * scope.timeScale
    assert calls[-2][1:] == ("set_cursor_position", ["VBARS", 1, -2.0 * scope.timeScale])
    assert calls[-1][1:] == ("set_cursor_position", ["VBARS", 2, 2.0 * scope.timeScale])
    assert scope.cursorWaveformDelta == 1.5
    scope.close()


def test_selected_channel_button_can_disable_trace():
    scope = controller()
    assert scope.channelEnabled(1)
    scope.pressChannel(1)
    assert not scope.channelEnabled(1)
    scope.close()


def test_vertical_detents_follow_probe_attenuation():
    scope = controller()
    assert scope.channelScale(1) == 0.5
    scope.adjustChannelScale(1, 1)
    assert scope.channelScale(1) == 0.2
    scope.openMenu("channel")
    scope.selectMenuItem(2)
    scope.selectSideItem(0)  # 1X
    scope.adjustChannelScale(1, 1)
    assert scope.channelScale(1) == 0.1
    scope.close()


def test_hardware_controller_can_switch_to_simulation(monkeypatch):
    class Signal:
        def connect(self, _callback): pass
        def emit(self, *_args): pass

    class Worker:
        resources_found = connection_changed = snapshot_ready = waveform_ready = Signal()
        measurements_ready = cursors_ready = diagnostics = operation_done = error = Signal()

    class Backend:
        worker = Worker()
        request_scan = request_connect = request_disconnect = request_invoke = Signal()
        def close(self): pass

    monkeypatch.setattr("mso2024_remote.qml_bridge.OscilloscopeController", lambda _parent: Backend())
    scope = ScopeController(simulation=False)
    scope.enableSimulation()
    assert scope.simulation
    assert scope.connected
    assert scope.identity.startswith("TEKTRONIX,MSO2024,SIMULATION")
    scope.close()


def test_disconnect_discards_pending_hardware_commands(monkeypatch):
    class Signal:
        def connect(self, _callback): pass
        def emit(self, *_args): pass

    class Worker:
        resources_found = connection_changed = snapshot_ready = waveform_ready = Signal()
        measurements_ready = cursors_ready = diagnostics = operation_done = error = Signal()

    class Backend:
        worker = Worker()
        request_scan = request_connect = request_disconnect = request_invoke = Signal()
        def close(self): pass

    monkeypatch.setattr("mso2024_remote.qml_bridge.OscilloscopeController", lambda _parent: Backend())
    scope = ScopeController(simulation=False)
    scope._connection_changed(True, "TEKTRONIX,MSO2024,0,1", "USB::SCOPE")
    scope._queue("scale1", "set_vertical_scale", [1, 0.5])
    assert "scale1" in scope._pending

    scope._connection_changed(False, "", "")

    assert scope._pending == {}
    assert not scope._flush_timer.isActive()
    scope.close()


def test_disconnected_hardware_commands_do_not_enter_queue(monkeypatch):
    class Signal:
        def connect(self, _callback): pass
        def emit(self, *_args): pass

    class Worker:
        resources_found = connection_changed = snapshot_ready = waveform_ready = Signal()
        measurements_ready = cursors_ready = diagnostics = operation_done = error = Signal()

    class Backend:
        worker = Worker()
        request_scan = request_connect = request_disconnect = request_invoke = Signal()
        def close(self): pass

    monkeypatch.setattr("mso2024_remote.qml_bridge.OscilloscopeController", lambda _parent: Backend())
    scope = ScopeController(simulation=False)

    scope._queue("scale1", "set_vertical_scale", [1, 0.5])

    assert scope._pending == {}
    assert not scope._flush_timer.isActive()
    scope.close()


def test_hardware_bus_menu_disables_unconfirmed_application_modules(monkeypatch):
    class Signal:
        def connect(self, _callback): pass
        def emit(self, *_args): pass
    class Worker:
        resources_found = connection_changed = snapshot_ready = waveform_ready = Signal()
        measurements_ready = cursors_ready = diagnostics = operation_done = error = Signal()
    class Backend:
        worker = Worker(); request_scan = request_connect = request_disconnect = request_invoke = Signal()
        def close(self): pass
    monkeypatch.setattr("mso2024_remote.qml_bridge.OscilloscopeController", lambda _parent: Backend())
    scope = ScopeController(False)
    scope.openBusMenu(1)
    scope.selectMenuItem(0)
    choices = {item["label"]: item for item in scope.sideMenu}
    assert choices["Parallel"]["enabled"]
    assert not choices["I2C"]["enabled"]
    assert "DPO2EMBD" in choices["I2C"]["reason"]
    scope.adjustMultipurpose("A", 1)
    assert scope.knobAValue == "Parallel"
    scope.close()


def test_hardware_bus_menu_enables_modules_reported_in_identity(monkeypatch):
    class Signal:
        def connect(self, _callback): pass
        def emit(self, *_args): pass
    class Worker:
        resources_found = connection_changed = snapshot_ready = waveform_ready = Signal()
        measurements_ready = cursors_ready = diagnostics = operation_done = error = Signal()
    class Backend:
        worker = Worker(); request_scan = request_connect = request_disconnect = request_invoke = Signal()
        def close(self): pass
    monkeypatch.setattr("mso2024_remote.qml_bridge.OscilloscopeController", lambda _parent: Backend())
    scope = ScopeController(False)
    scope._connection_changed(True, "TEKTRONIX,MSO2024,0,DPO2EMBD:v1.0", "USB::SCOPE")
    scope.openBusMenu(1)
    choices = {item["label"]: item for item in scope.sideMenu}
    assert choices["I2C"]["enabled"]
    assert choices["SPI"]["enabled"]
    assert not choices["CAN"]["enabled"]
    scope.close()
