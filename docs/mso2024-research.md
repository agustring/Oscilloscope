# MSO2024 interaction research

This is the Step 1 design reference for the QML redesign. It targets the original
Tektronix **MSO2024 / MSO2000 family**, not the MSO2024B and not the modern
MSO24. Where the later combined manual differs, the original-series programmer
manual (077-0097-01) remains the SCPI authority.

## Primary sources

- Tektronix, *MSO2000 and DPO2000 Series Oscilloscopes User Manual*,
  071-2319-02 Rev. A: <https://download.tek.com/manual/071231902_RevA_web_1.pdf>
- Tektronix, *DPO2000 and MSO2000 Series Programmer Manual*, 077-0097-01 Rev. A:
  <https://download.tek.com/manual/077009701_RevA_web.pdf>
- Tektronix, *MSO2000/DPO2000 Mixed Signal Oscilloscopes Datasheet*:
  <https://www.tek.com/en/datasheet/mso2000-dpo2000-series>
- Tektronix original-series downloads, including firmware and option manuals:
  <https://www.tek.com/en/support/datasheets-manuals-software-downloads?model=dpo2024>

Page references below use PDF page numbers (not the printed page number).

## Confirmed physical organization

The instrument is a 4+16-channel, 200 MHz model with a 7-inch WQVGA widescreen
display, 1 GS/s sampling, and a 1 Mpoint maximum record. The UI should preserve
the dense landscape display and the physical groups visible in the manual's
front-panel survey (user manual pp. 45-52):

- display with six lower-bezel keys and five side-bezel keys;
- dedicated Measure, Search, Test, Acquire, Autoset, Trigger Menu, Utility, and
  Save/Recall buttons;
- CH1-CH4, B1/B2, Math, Reference, and D15-D0 source/menu buttons;
- two general-purpose encoders, `a` above `b`, with on-screen assignment icons;
- Cursors, Select, Fine, FilterVu, and Intensity controls;
- Wave Inspector concentric Pan/Zoom encoder plus Zoom, play/pause, previous,
  set/clear mark, and next controls;
- Horizontal Position and Scale;
- Run/Stop, Single, Autoset;
- Trigger Level (push sets 50%) and Force Trig;
- a Position and Scale pair for every analog channel;
- Save, Default Setup, Menu Off, and Waveform Only.

The virtual panel should follow these groups rather than arranging features as
application settings. PC-only connection, debug, fullscreen, and mode controls
belong in a restrained frame around the panel, not inside the emulated bezel.

## Menu interaction grammar

The original workflow is explicit (user manual pp. 45-47):

1. A front-panel menu button selects the current context.
2. A lower-bezel key selects one category. Pressing it again may cycle a pop-up
   choice or dismiss its side menu.
3. A side-bezel key selects a detailed choice; repeated presses may cycle values.
4. Pop-out lists and numeric values bind to multipurpose knob A, or A and B.
5. `Fine` changes the adjustment granularity. `Menu Off` dismisses menus.

Consequently, QML needs one centralized menu state with at least
`context`, `bottomSelection`, `sideMenu`, `knobABinding`, and `knobBBinding`.
Individual buttons must not independently toggle unrelated visibility.

## Display anatomy

The display survey (user manual pp. 53-56) identifies these persistent layers:

- acquisition status: Run, Stop, Roll, or PreVu;
- trigger status: Trig'd, Auto, PrTrig, or Trig?;
- trigger position and expansion-point markers;
- waveform-record overview and horizontal position/scale readouts;
- trigger type, source, and level readouts;
- channel baseline markers and channel readouts showing scale, coupling, invert,
  and bandwidth state;
- measurements, cursor readouts, and bus/digital-channel indicators as active;
- lower and right menu overlays, which reduce the available graticule area.

The graticule and traces should be scene-graph or painted geometry, not one QML
object per sample. Data acquisition and render data remain separate. Menus and
markers are overlay layers above the trace geometry.

## Color identity

The original front-panel and screen figures consistently identify the four
analog channels as CH1 yellow, CH2 cyan, CH3 magenta, and CH4 green. The same
token must drive the input button, scale/position controls, baseline marker,
trace, channel readout, and measurement source. Digital channels use the
resistor color code (the manual explicitly begins D0 black, D1 brown, D2 red on
p. 56), so analog and digital palettes must be separate theme tables.

## Context menus to reproduce

### Analog channel

Pressing CH1-CH4 both displays/removes that waveform and opens its vertical
menu (pp. 48, 51-52, and 100-102). The context covers coupling, bandwidth,
probe setup, invert, label, and related input settings. Position and scale stay
on their dedicated encoders; the screen readout reflects scale, coupling,
invert, and bandwidth.

### Acquire / display

Acquire controls acquisition mode and record length (p. 47). The documented
representative lower menu (p. 95) is: averaging/acquisition mode, Record Length,
Delay, Set Horizontal Position to 0 s, Waveform Display, XY Display, and
Acquisition Details. Waveform Display opens a side menu for persistence time,
automatic persistence, and clearing persistence (pp. 95-96).

The original programmer manual documents `ACQuire:MODe` values Sample and
Average. Peak-detect or Hi-Res choices must not be invented from newer models.

### Trigger

The verified trigger types are Edge, Pulse Width, Runt, Logic, Setup & Hold,
Rise/Fall Time, Video, and Bus (user manual p. 86). The Edge lower menu is:
Type, Source, Coupling, Slope, Level, and Mode & Holdoff. Other trigger types
replace the lower categories with type-specific parameters rather than opening
a generic settings form.

Bus is capability-gated. Parallel bus support is intrinsic to an MSO2000;
serial protocols require modules: DPO2EMBD for I2C/SPI, DPO2AUTO for CAN/LIN,
and DPO2COMP for RS-232/422/485/UART (pp. 48-49 and 86). Unsupported entries
should remain visible but disabled with the missing-module reason.

The programmer manual verifies `BUS:B<x>:TYPE` values I2C, SPI, CAN, RS232C,
PARallel, and LIN, plus `BUS:B<x>:STATE` for display enablement (p. 89). The
bridge may unlock module-dependent entries when a connected instrument reports
the corresponding DPO2 module in its identity; otherwise it remains
conservative rather than probing by changing the instrument configuration.

### Measure and cursors

The Measure lower menu is documented on p. 108: Add Measurement, Remove
Measurement, Indicators, Gating, High-Low Method, Bring Cursors on Screen, and
Configure Cursors. Add Measurement assigns knob A to measurement type and knob
B to source, followed by a side-bezel confirmation. Remove Measurement opens a
side menu listing active measurements plus Remove All.

The Cursors button cycles through none, two waveform-linked vertical cursors,
and four screen cursors (pp. 49-50 and 115-117). Multipurpose A/B move cursors;
Select links/unlinks a pair or switches the active axis when both axes exist.

### Search and Wave Inspector

Wave Inspector is a physical navigation subsystem, not a generic zoom toolbar.
Its outer ring pans; its inner knob zooms. Play/pause automatically pans, with
direction and speed controlled by Pan. Previous/Next jump among marks and
Set/Clear toggles a mark (pp. 50-51 and 124-128).

Search is deliberately similar to Trigger. Its top-level lower menu contains
Search On/Off, Save All Marks, Clear All Marks, copy Search settings to Trigger,
and copy Trigger settings to Search. Search Type then exposes Edge, Pulse
Width, Runt, Logic, Setup & Hold, Rise/Fall Time, or Bus parameters. Hollow
triangles denote automatic marks; solid triangles denote user marks.

### Utility, Save/Recall, bus, math, and reference

- Utility includes system tasks such as language and date/time; it should be a
  contextual menu, not a permanent settings sidebar.
- Save/Recall manages setups, waveforms, and screen images in internal or USB
  storage. Save performs the currently configured immediate save.
- B1/B2 define and show a bus; the side menu depends on the selected protocol
  and installed module.
- Math and Reference independently manage their displayed waveforms.
- Waveform Only temporarily removes menus and readouts and restores them on a
  second press (p. 52).

## Multipurpose and encoder behavior

The screen must always say what A and B currently control. A selects pop-out
choices and edits numeric values; B is activated when a second value/source or
cursor is needed. Intensity assigns A to waveform intensity and B to graticule
intensity. Fine applies to A/B and the vertical/horizontal position and trigger
level encoders (pp. 49-50).

The QML rotary component should therefore emit semantic detents and push events,
not expose a free continuous value. Mouse wheel, vertical drag, arrows, and
Page Up/Down all resolve to detents; Shift maps to Fine. The controller chooses
the permitted discrete instrument value and coalesces rapid changes before
sending the latest SCPI command.

## SCPI and capability guardrails

- QML contains no SCPI strings. The Python driver remains the only SCPI layer.
- Original-series manual 077-0097-01 is authoritative for every exposed value.
- Query installed options before enabling serial bus UI; do not infer options
  merely from the model name.
- UI changes are optimistic but provisional until a worker-thread query confirms
  instrument state. Rejected values revert to the confirmed state.
- VISA work stays off the GUI thread and high-frequency controls are coalesced.
- The specifications manual confirms the 1X vertical sensitivity sequence as
  2 mV/div through 5 V/div in 1-2-5 steps. The programmer manual confirms the
  MSO2024 horizontal range as 2 ns/div through 100 s/div; the UI uses the
  instrument's 1-2-5 front-panel sequence and tests both endpoints.

## Implications for Step 2

The next deliverable should define one shared `ScopeState`, a declarative menu
model, the QML component tree, and two static mockups (front panel and enhanced
mode). It should first cover simulation and the representative states: default
display, CH1, Acquire, Trigger/Edge, Measure/Add Measurement, Cursors, Search,
and Wave Inspector zoom. Hardware integration should reuse the existing tested
driver and worker rather than rewrite it during the visual migration.
