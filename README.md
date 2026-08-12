# Tektronix MSO2024 Remote

A Python desktop remote front panel for the original Tektronix **MSO2024**. The
application discovers the instrument through VISA, verifies it with `*IDN?`,
downloads properly scaled binary waveforms, and sends front-panel changes back
to the physical oscilloscope.

## Features

- Automatic VISA discovery and strict Tektronix MSO2024 identity check
- Responsive PySide6 GUI with all VISA access isolated in a worker thread
- CH1–CH4 display, enable, scale, position, coupling, probe attenuation,
  20 MHz bandwidth limit, invert, and channel label
- Signed, little-endian binary waveform transfer with IEEE block parsing and
  `XINCR`, `XZERO`, `PT_OFF`, `YMULT`, `YOFF`, and `YZERO` conversion
- Time/division, trigger position, delay, and 100 k/1 M record length
- Run, Stop, Single Sequence, and Autoset
- Wheel changes the selected channel's real V/div; Ctrl+wheel changes the
  oscilloscope's real time/div
- Horizontal dragging changes instrument delay; double-click centers the view
- Edge, pulse-width, runt, transition-time, logic, setup/hold, video, and
  option-dependent serial-bus trigger selection
- Four hardware measurement slots using the instrument's own measurement engine
- Time/voltage cursors that can also be dragged on the waveform plot
- Full-resolution CSV waveform export
- SCPI console with Up/Down command history
- Diagnostics with last command, last response, VISA errors, and `ALLEv?`
- Staggered synchronization for front-panel changes made on the oscilloscope

## Requirements

- Python 3.10 or newer (3.11 recommended)
- Windows, Linux, or macOS
- A VISA implementation. On Windows, install either:
  - [NI-VISA](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html), or
  - Tektronix TekVISA (available from the MSO2024 support downloads page)
- A USB cable connected to the MSO2024 USB device port

PyVISA is an API layer. This project installs `pyvisa-py`, PyUSB, and a libusb
runtime as a fallback,
but NI-VISA or TekVISA is recommended for this Windows USBTMC instrument. The
application prefers an installed system VISA library and otherwise uses the
Python backend.

## Install and run

From this directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

On Linux or macOS, activate with `source .venv/bin/activate` instead.

Connect and turn on the oscilloscope before starting the application. The app
scans all VISA resources and queries each with `*IDN?`; verified MSO2024 entries
appear first. Select one and press **Connect**. No VISA resource string is
hardcoded.

If discovery fails, open **Diagnostics** and check:

1. The scope appears in NI MAX or the vendor VISA utility.
2. A 64-bit VISA runtime is installed for a 64-bit Python installation.
3. No other program holds the USBTMC session exclusively.
4. The VISA timeout is high enough for full-resolution transfers.

To inspect the active backend, run `pyvisa-info`. If it shows an IVI binary as
not found but lists the `py` backend, the Python fallback is active. If the
fallback finds no USB resources, install NI-VISA or the MSO2024-compatible
TekVISA package rather than replacing the instrument driver blindly with Zadig;
changing a Windows USB driver can prevent vendor VISA software from using it.

## Controls

- Click a trace or select its channel tab to choose the active channel.
- Wheel over the plot changes that channel's hardware V/div in 1-2-5 steps.
- Ctrl+wheel changes the hardware time/div in 1-2-5 steps.
- Drag horizontally to update horizontal delay on the instrument.
- Double-click the plot to restore channel position to zero and trigger
  position to 50%.
- Choose cursor type in **Cursors**. Drag orange plot lines to change the
  physical scope cursors.
- **SAVE WAVEFORM** downloads the selected channel at full resolution and
  writes `time_s,voltage_V` CSV columns.

## Instrument-specific limitations

These are intentional and are not silently emulated on the PC:

- `ACQuire:MODe` in the MSO2000 programming manual accepts `SAMple` and
  `AVErage`. Therefore the GUI does not issue invented Peak Detect, Envelope,
  or Hi-Res mode values. Peak-detect data can exist as `COMPOSITE_ENV`, but that
  is waveform composition, not a documented MSO2024 `ACQUIRE:MODE` setting.
- Average counts are powers of two from 2 through 512.
- Nominal record lengths are 100,000 and 1,000,000 points. The returned actual
  record can be 125,000 or 1,250,000 for some horizontal settings.
- Edge trigger slope supports Rise and Fall, not Either. Transition trigger does
  support Either polarity.
- Serial-bus trigger requires the appropriate DPO2AUTO or DPO2EMBD application
  module and a configured B1/B2 bus.
- The instrument exposes four automatic measurement slots, so the GUI allows
  four simultaneous measurements.
- Delay and Phase use the second source selector shown beside the primary source.
  Their advanced edge-direction settings remain available through the SCPI
  console. Logic pattern/state and Setup/Hold panels expose the documented
  analog/digital sources, input states, clock edges, thresholds, and time values.

## SCPI and waveform implementation

Raw SCPI strings live in `mso2024_remote/instrument/mso2024.py`, not in GUI
widgets. Each feature has an adjacent comment naming the documented SCPI
command. Waveforms use `DATA:ENCDG SRIBINARY` and two-byte samples. The parser
honors the returned signedness, byte order, and byte width rather than assuming
them. It applies the official equations:

```text
X[n] = XZERO + (n - PT_OFF) * XINCR
Y[n] = YZERO + (raw[n] - YOFF) * YMULT
```

The transfer selects `COMPOSITE_YT` or `SINGULAR_YT` based on
`DATA:COMPOSITION:AVAILABLE?`, preventing envelope min/max pairs from being
mistaken for ordinary samples.

## Manuals used

The implementation was checked against official Tektronix sources:

- [DPO2000 and MSO2000 Series Programmer Manual, 077-0097-01 Rev A](https://download.tek.com/manual/077009701_RevA_web.pdf) — explicitly applies to MSO2024; primary command and waveform reference
- [Tektronix MSO2024 support/download page](https://www.tek.com/en/support/datasheets-manuals-software-downloads?model=dpo2024) — programmer manual, user manuals, firmware, drivers, and TekVISA

The programmer manual is the authority when its command set differs from feature
lists for newer MSO2000B/MDO families.

## Tests

Install test dependencies and run:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The tests cover binary block framing, signed endianness, waveform scaling,
command sequences, probe attenuation semantics, trigger vocabulary, and input
limits. Hardware-in-the-loop behavior should additionally be verified against
the particular scope firmware and installed option modules.

## Project structure

```text
mso2024_remote/
├── instrument/       VISA session, SCPI façade, waveform parser
├── workers/          thread-confined polling and acquisition worker
├── gui/              focused PySide6 panels and waveform view
├── controller.py     queued GUI/worker bridge
└── main.py           application bootstrap
tests/                unit tests without physical hardware
main.py               convenient launcher
```
