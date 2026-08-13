# QML redesign architecture

## State flow

```text
QML controls -> ScopeController slots -> optimistic ScopeState
                                  -> coalesced backend command
worker/simulator -> confirmed state and waveform -> QML properties
```

`ScopeController` is the only QML context object. QML never imports PyVISA or
contains SCPI. The simulator and VISA worker present the same state shape.

## Component tree

```text
Main.qml
|- ConnectionOverlay
|- ScopeDisplay
|  |- Graticule + WaveformCanvas
|  |- status/channel/measurement overlays
|  |- SideBezelMenu
|  `- BottomBezelMenu
|- MultipurposeControls
|- HorizontalControls
|- TriggerControls
|- VerticalControls
`- WaveInspectorControls
```

Reusable primitives include `ScopeButton`, `SoftKey`, `RotaryKnob`, and the
concentric `PanZoomKnob`. `ScopeTheme` centralizes dimensions and channel
colors. A single `menuContext` plus `menuSelection` drives all bezel content
and A/B assignments.

## Layout mockups

Front panel keeps the display dominant on the left, the A/B, horizontal,
acquisition, and trigger groups on the right, and four vertical channel strips
below. Enhanced mode uses the same display and state but collapses the physical
groups into a compact bottom control rail. Additional width always goes first
to the display; knobs have bounded sizes. Below 730 px window height, the
enhanced layout is selected automatically to keep every visible control usable.

## Implemented verification slice

The executable slice launches with `python -m mso2024_remote.main --simulation`,
shows animated CH1-CH4 traces, supports discrete channel/timebase detents,
switches all main bezel contexts, exposes A/B assignments, implements
Run/Stop/Single/Autoset and Wave Inspector controls, and toggles fullscreen with
F11. Headless QML loading and driver/bridge behavior are covered by tests.
