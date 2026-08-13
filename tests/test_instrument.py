import pytest

from mso2024_remote.instrument.mso2024 import TektronixMSO2024


class FakeResource:
    def __init__(self, responses=None):
        self.commands = []
        self.read_termination = "\n"
        self.responses = responses or {}

    def write(self, command):
        self.commands.append(command)

    def query(self, command):
        self.commands.append(command)
        return self.responses[command]


class FakeConnection:
    def __init__(self):
        self.resource = FakeResource()


def scope():
    return TektronixMSO2024(FakeConnection())


def test_run_and_single_use_documented_stop_after_sequence():
    instrument = scope()
    instrument.run()
    instrument.single()
    assert instrument.resource.commands == [
        "ACQUIRE:STOPAFTER RUNSTOP",
        "ACQUIRE:STATE RUN",
        "ACQUIRE:STOPAFTER SEQUENCE",
        "ACQUIRE:STATE RUN",
    ]


def test_force_trigger_uses_documented_command():
    instrument = scope()
    instrument.force_trigger()
    assert instrument.resource.commands == ["TRIGGER FORCE"]


def test_trigger_level_targets_the_selected_analog_channel():
    instrument = scope()
    instrument.set_trigger_level(3, -0.125)
    assert instrument.resource.commands == ["TRIGGER:A:LEVEL:CH3 -0.125"]


def test_horizontal_position_and_delay_select_the_matching_instrument_mode():
    instrument = scope()
    instrument.set_horizontal_position(62.5)
    instrument.set_delay(-0.00025)
    assert instrument.resource.commands == [
        "HORIZONTAL:DELAY:MODE OFF",
        "HORIZONTAL:POSITION 62.5",
        "HORIZONTAL:DELAY:MODE ON",
        "HORIZONTAL:DELAY:TIME -0.00025",
    ]


def test_test_button_uses_documented_front_panel_command():
    instrument = scope()
    instrument.open_test_menu()
    assert instrument.resource.commands == ["FPANEL:PRESS TEST"]


def test_bus_type_uses_original_mso2000_bus_commands():
    instrument = scope()
    instrument.set_bus_type(2, "RS-232")
    assert instrument.resource.commands == ["BUS:B2:TYPE RS232C", "BUS:B2:STATE ON"]


def test_measurement_menu_helpers_use_documented_commands():
    instrument = scope()
    instrument.set_measurement_indicators(2)
    instrument.set_measurement_gating("cursor")
    instrument.set_measurement_method("minmax")
    assert instrument.resource.commands == [
        "MEASUREMENT:INDICATORS:STATE MEAS2",
        "MEASUREMENT:GATING CURSOR",
        "MEASUREMENT:METHOD MINMAX",
    ]


def test_wave_inspector_uses_documented_zoom_and_mark_commands():
    instrument = scope()
    instrument.set_zoom_enabled(True)
    instrument.set_zoom_scale(0.01)
    instrument.set_zoom_position(60)
    instrument.move_to_mark("previous")
    instrument.create_mark("CH2")
    assert instrument.resource.commands == [
        "ZOOM:MODE ON",
        "ZOOM:ZOOM1:SCALE 0.01",
        "ZOOM:ZOOM1:POSITION 60",
        "MARK PREVIOUS",
        "MARK:CREATE CH2",
    ]


def test_wave_inspector_play_pause_uses_documented_front_panel_argument():
    instrument = scope()
    instrument.toggle_wave_inspector_playback()
    assert instrument.resource.commands == ["FPANEL:PRESS PAUSE"]


def test_wave_inspector_set_clear_uses_documented_front_panel_argument():
    instrument = scope()
    instrument.toggle_mark()
    assert instrument.resource.commands == ["FPANEL:PRESS MARK"]


def test_wave_inspector_zoom_state_uses_documented_queries():
    connection = FakeConnection()
    connection.resource = FakeResource({
        "ZOOM:MODE?": "ON",
        "ZOOM:ZOOM1:SCALE?": "0.002",
        "ZOOM:ZOOM1:POSITION?": "62.5",
    })
    instrument = TektronixMSO2024(connection)

    assert instrument.zoom_state() == {"enabled": True, "scale": 0.002, "position": 62.5}
    assert instrument.resource.commands == [
        "ZOOM:MODE?", "ZOOM:ZOOM1:SCALE?", "ZOOM:ZOOM1:POSITION?"
    ]


def test_waveform_cursor_readback_includes_amplitude_and_link_mode():
    connection = FakeConnection()
    connection.resource = FakeResource({
        "CURSOR:FUNCTION?": "WAVEFORM",
        "CURSOR:VBARS:POSITION1?": "-0.001",
        "CURSOR:VBARS:POSITION2?": "0.002",
        "CURSOR:VBARS:DELTA?": "0.003",
        "CURSOR:VBARS:VDELTA?": "1.25",
        "CURSOR:MODE?": "TRACK",
    })
    instrument = TektronixMSO2024(connection)

    assert instrument.cursor_state() == {
        "function": "WAVEFORM", "x1": -0.001, "x2": 0.002,
        "dx": 0.003, "vdelta": 1.25, "mode": "TRACK",
    }


def test_cursor_link_mode_uses_documented_command():
    instrument = scope()
    instrument.set_cursor_mode("track")
    assert instrument.resource.commands == ["CURSOR:MODE TRACK"]


def test_trigger_system_state_uses_documented_query():
    connection = FakeConnection()
    connection.resource = FakeResource({"TRIGGER:STATE?": ":TRIGGER:STATE READY"})
    instrument = TektronixMSO2024(connection)

    assert instrument.trigger_system_state() == "READY"
    assert instrument.resource.commands == ["TRIGGER:STATE?"]


def test_search_commands_use_original_series_vocabulary():
    instrument = scope()
    instrument.set_search_enabled(True)
    instrument.set_search_kind("Rise/Fall Time")
    instrument.copy_search_settings(True)
    assert instrument.resource.commands == [
        "SEARCH:SEARCH1:STATE ON",
        "SEARCH:SEARCH1:TRIGGER:A:TYPE TRANSITION",
        "SEARCH:SEARCH1:COPY SEARCHTOTRIGGER",
    ]


def test_search_criteria_use_dedicated_search_command_tree():
    instrument = scope()
    instrument.configure_edge_search("CH2", "fall", 0.75)
    instrument.configure_pulse_search("Pulse Width", "CH1", "positive", "morethan", 1e-6)
    instrument.configure_logic_search("high", "low", "x", "x", "lessthan", 2e-6)
    instrument.set_search_bus_source(2)
    assert instrument.resource.commands == [
        "SEARCH:SEARCH1:TRIGGER:A:EDGE:SOURCE CH2",
        "SEARCH:SEARCH1:TRIGGER:A:EDGE:SLOPE FALL",
        "SEARCH:SEARCH1:TRIGGER:A:LEVEL 0.75",
        "SEARCH:SEARCH1:TRIGGER:A:PULSEWIDTH:SOURCE CH1",
        "SEARCH:SEARCH1:TRIGGER:A:PULSEWIDTH:POLARITY POSITIVE",
        "SEARCH:SEARCH1:TRIGGER:A:PULSEWIDTH:WHEN MORETHAN",
        "SEARCH:SEARCH1:TRIGGER:A:PULSEWIDTH:WIDTH 1e-06",
        "SEARCH:SEARCH1:TRIGGER:A:LOGIC:PATTERN:INPUT:CH1 HIGH",
        "SEARCH:SEARCH1:TRIGGER:A:LOGIC:PATTERN:INPUT:CH2 LOW",
        "SEARCH:SEARCH1:TRIGGER:A:LOGIC:PATTERN:INPUT:CH3 X",
        "SEARCH:SEARCH1:TRIGGER:A:LOGIC:PATTERN:INPUT:CH4 X",
        "SEARCH:SEARCH1:TRIGGER:A:LOGIC:PATTERN:WHEN LESSTHAN",
        "SEARCH:SEARCH1:TRIGGER:A:LOGIC:PATTERN:WHEN:LESSLIMIT 2e-06",
        "SEARCH:SEARCH1:TRIGGER:A:BUS:SOURCE B2",
    ]


def test_setup_hold_search_writes_sources_thresholds_and_times():
    instrument = scope()
    instrument.configure_setup_hold_search("CH1", "rise", 1.4, "D0", 1.4, 1e-9, 2e-9)
    assert instrument.resource.commands == [
        "SEARCH:SEARCH1:TRIGGER:A:SETHOLD:CLOCK:SOURCE CH1",
        "SEARCH:SEARCH1:TRIGGER:A:SETHOLD:CLOCK:EDGE RISE",
        "SEARCH:SEARCH1:TRIGGER:A:SETHOLD:CLOCK:THRESHOLD 1.4",
        "SEARCH:SEARCH1:TRIGGER:A:SETHOLD:DATA:SOURCE D0",
        "SEARCH:SEARCH1:TRIGGER:A:SETHOLD:DATA:THRESHOLD 1.4",
        "SEARCH:SEARCH1:TRIGGER:A:SETHOLD:SETTIME 1e-09",
        "SEARCH:SEARCH1:TRIGGER:A:SETHOLD:HOLDTIME 2e-09",
    ]


def test_math_reference_and_setup_commands_are_documented_forms():
    instrument = scope()
    instrument.configure_math("CH1 * CH2")
    instrument.set_reference_enabled(1, True)
    instrument.save_setup(3)
    instrument.recall_setup(3)
    instrument.default_setup()
    assert instrument.resource.commands == [
        "MATH1:TYPE DUAL",
        'MATH1:DEFINE "CH1*CH2"',
        "SELECT:MATH ON",
        "SELECT:REF1 ON",
        "SAVE:SETUP 3",
        "RECALL:SETUP 3",
        "RECALL:SETUP FACTORY",
    ]


def test_probe_attenuation_is_converted_to_probe_gain():
    instrument = scope()
    instrument.set_probe_attenuation(1, 10)
    assert instrument.resource.commands[-1] == "CH1:PROBE:GAIN 0.1"


def test_invalid_scales_are_rejected_before_io():
    instrument = scope()
    with pytest.raises(ValueError):
        instrument.set_time_scale(1e-10)
    with pytest.raises(ValueError):
        instrument.set_vertical_position(1, 5)
    assert instrument.resource.commands == []


def test_transition_trigger_uses_transition_vocabulary():
    instrument = scope()
    instrument.set_pulse_parameter("Rise/Fall Time", "EITHER", "FASTER", 2e-9)
    assert instrument.resource.commands == [
        "TRIGGER:A:TRANSITION:POLARITY EITHER",
        "TRIGGER:A:TRANSITION:WHEN FASTER",
        "TRIGGER:A:TRANSITION:DELTATIME 2e-09",
    ]


def test_logic_trigger_configures_real_pattern_inputs():
    instrument = scope()
    instrument.configure_logic_trigger(
        "HIGH", "LOW", "X", "X", "AND", "MORETHAN", 1e-6, "NONE", "RISE"
    )
    assert instrument.resource.commands[-2:] == [
        "TRIGGER:A:LOGIC:PATTERN:WHEN MORETHAN",
        "TRIGGER:A:LOGIC:PATTERN:DELTATIME 1e-06",
    ]


def test_logic_trigger_configures_digital_inputs_and_threshold():
    instrument = scope()
    instrument.configure_logic_trigger(
        "HIGH", "LOW", "X", "X", "AND", "TRUE", 1e-6,
        digital_inputs=("LOW", "HIGH", "X", "X"),
        threshold_source="D15",
        threshold=-1.3,
    )
    assert instrument.resource.commands[5:10] == [
        "TRIGGER:A:LOGIC:INPUT:D0 LOW",
        "TRIGGER:A:LOGIC:INPUT:D1 HIGH",
        "TRIGGER:A:LOGIC:INPUT:D2 X",
        "TRIGGER:A:LOGIC:INPUT:D3 X",
        "TRIGGER:A:LOGIC:THRESHOLD:D15 -1.3",
    ]


def test_invalid_digital_logic_input_is_rejected_before_io():
    instrument = scope()
    with pytest.raises(ValueError, match="four HIGH, LOW, or X"):
        instrument.configure_logic_trigger(
            "HIGH", "LOW", "X", "X", "AND", "TRUE", 1e-6,
            digital_inputs=("HIGH",),
        )
    assert instrument.resource.commands == []


def test_setup_hold_requires_different_sources():
    instrument = scope()
    with pytest.raises(ValueError, match="must differ"):
        instrument.configure_setup_hold_trigger("CH1", "RISE", 1.0, "CH1", 1.0, 1e-9, 1e-9)
