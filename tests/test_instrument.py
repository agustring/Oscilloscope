import pytest

from mso2024_remote.instrument.mso2024 import TektronixMSO2024


class FakeResource:
    def __init__(self):
        self.commands = []
        self.read_termination = "\n"

    def write(self, command):
        self.commands.append(command)


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


def test_setup_hold_requires_different_sources():
    instrument = scope()
    with pytest.raises(ValueError, match="must differ"):
        instrument.configure_setup_hold_trigger("CH1", "RISE", 1.0, "CH1", 1.0, 1e-9, 1e-9)
