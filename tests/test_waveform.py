import numpy as np
import pytest

from mso2024_remote.instrument.waveform import (
    WaveformPreamble,
    decode_samples,
    extract_ieee_block,
    parse_waveform,
)


def test_extract_ieee_block_tolerates_curve_prefix_and_newline():
    assert extract_ieee_block(b":CURVE #14\x01\x02\x03\x04\n") == b"\x01\x02\x03\x04"


def test_extract_ieee_block_rejects_truncation():
    with pytest.raises(ValueError, match="Truncated"):
        extract_ieee_block(b"#15abc")


@pytest.mark.parametrize(
    ("order", "payload"),
    [("LSB", b"\x01\x00\xfe\xff"), ("MSB", b"\x00\x01\xff\xfe")],
)
def test_decode_signed_16_bit_endianness(order, payload):
    preamble = WaveformPreamble(1, 0, 1, 0, 0, byte_order=order)
    np.testing.assert_array_equal(decode_samples(payload, preamble), [1, -2])


def test_parse_waveform_uses_tektronix_scaling_equations():
    # IEEE payload contains signed levels [10, 12, 14].
    raw = b"#16" + np.array([10, 12, 14], dtype="<i2").tobytes() + b"\n"
    preamble = WaveformPreamble(
        x_increment=0.5,
        x_zero=-1.0,
        y_multiplier=0.25,
        y_offset=10.0,
        y_zero=1.5,
        point_offset=1.0,
        byte_width=2,
        binary_format="RI",
        byte_order="LSB",
    )
    waveform = parse_waveform(2, raw, preamble)
    np.testing.assert_allclose(waveform.time, [-1.5, -1.0, -0.5])
    np.testing.assert_allclose(waveform.voltage, [1.5, 2.0, 2.5])
    assert waveform.channel == 2
