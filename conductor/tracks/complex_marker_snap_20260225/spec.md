# Specification: Fix Complex Marker Snapping While Dragging

## Overview
Markers in complex-data lenses (Real, Imag, Magnitude, Phase) currently exhibit "lazy snapping" where the marker follows the mouse cursor freely while the mouse button is held down, and only snaps to the nearest point on the trace upon release. This differs from the behavior in real-valued waveform lenses, where markers are strictly constrained to and slide smoothly along the trace throughout the entire drag operation.

## Functional Requirements
- **Real-time Trace Snapping:** Markers in all complex-data lenses (except Constellation) MUST remain strictly attached to the nearest point on the signal trace while the user is dragging them (mouse button held down).
- **Parity with Real Data:** The user experience when dragging markers on complex data should be identical to the smooth, constrained dragging experience seen with real-valued waveform data.
- **Affected Lenses:**
    - Real Waveform (Complex Data)
    - Imag Waveform (Complex Data)
    - FFT Magnitude (Complex Data)
    - FFT Phase (Complex Data)
- **Excluded Lenses:**
    - Constellation (Markers here should NOT be constrained to the trace in the same way, as it's a scatter plot of points, not necessarily a continuous temporal trace).

## Acceptance Criteria
- [ ] Dragging a marker in the 'Real' lens of a complex probe results in the marker sliding strictly along the plotted curve.
- [ ] Dragging a marker in the 'Imag' lens of a complex probe results in the marker sliding strictly along the plotted curve.
- [ ] Dragging a marker in the 'FFT Mag (dB)' lens results in the marker sliding strictly along the spectral trace.
- [ ] The marker DOES NOT "float" away from the trace during the drag operation.
- [ ] No regression in 'Constellation' lens behavior or real-valued waveform marker behavior.

## Out of Scope
- Changing marker behavior for the Constellation lens.
- Adding new marker types or visual styles.
