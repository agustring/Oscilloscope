from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class WaveformPreamble:
    """Metadata returned by the MSO2024 WFMOutpre queries."""

    x_increment: float
    x_zero: float
    y_multiplier: float
    y_offset: float
    y_zero: float
    point_offset: float = 0.0
    byte_width: int = 2
    binary_format: str = "RI"
    byte_order: str = "LSB"
    point_format: str = "Y"
    x_unit: str = "s"
    y_unit: str = "V"


@dataclass(frozen=True)
class Waveform:
    channel: int
    time: np.ndarray
    voltage: np.ndarray
    preamble: WaveformPreamble


def extract_ieee_block(raw: bytes) -> bytes:
    """Extract an IEEE 488.2 definite-length block, tolerating a SCPI prefix."""
    marker = raw.find(b"#")
    if marker < 0 or marker + 2 > len(raw):
        raise ValueError("CURVE? response does not contain an IEEE binary block")
    digits_byte = raw[marker + 1 : marker + 2]
    if not digits_byte.isdigit():
        raise ValueError("Invalid IEEE binary block length header")
    digits = int(digits_byte)
    if digits == 0:
        raise ValueError("Indefinite IEEE binary blocks are not supported")
    length_start = marker + 2
    length_end = length_start + digits
    if length_end > len(raw):
        raise ValueError("Truncated IEEE binary block header")
    length_text = raw[length_start:length_end]
    if not length_text.isdigit():
        raise ValueError("Invalid IEEE binary block payload length")
    payload_length = int(length_text)
    payload_end = length_end + payload_length
    if payload_end > len(raw):
        raise ValueError(
            f"Truncated IEEE binary block: expected {payload_length} bytes, "
            f"received {len(raw) - length_end}"
        )
    return raw[length_end:payload_end]


def decode_samples(payload: bytes, preamble: WaveformPreamble) -> np.ndarray:
    """Decode signed/unsigned one- or two-byte waveform samples."""
    signed = preamble.binary_format.upper().startswith("RI")
    if preamble.byte_width == 1:
        dtype = np.dtype("i1" if signed else "u1")
    elif preamble.byte_width == 2:
        endian = "<" if preamble.byte_order.upper().startswith("LSB") else ">"
        dtype = np.dtype(endian + ("i2" if signed else "u2"))
    else:
        raise ValueError(f"Unsupported waveform byte width: {preamble.byte_width}")
    if len(payload) % preamble.byte_width:
        raise ValueError("Waveform payload length is not aligned to sample width")
    return np.frombuffer(payload, dtype=dtype).astype(np.float64, copy=False)


def scale_waveform(
    channel: int, raw_samples: np.ndarray, preamble: WaveformPreamble
) -> Waveform:
    """Convert digitizer levels to physical time and voltage values."""
    index = np.arange(raw_samples.size, dtype=np.float64)
    time = preamble.x_zero + (index - preamble.point_offset) * preamble.x_increment
    voltage = (
        (raw_samples.astype(np.float64, copy=False) - preamble.y_offset)
        * preamble.y_multiplier
        + preamble.y_zero
    )
    return Waveform(channel=channel, time=time, voltage=voltage, preamble=preamble)


def parse_waveform(channel: int, raw: bytes, preamble: WaveformPreamble) -> Waveform:
    return scale_waveform(channel, decode_samples(extract_ieee_block(raw), preamble), preamble)
