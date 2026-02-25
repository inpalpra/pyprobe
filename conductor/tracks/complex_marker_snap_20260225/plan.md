# Implementation Plan: Fix Complex Marker Snapping While Dragging

This plan outlines the steps to implement continuous, smooth marker snapping to traces for complex-data lenses in PyProbe, matching the existing behavior of real-valued waveform lenses.

## Phase 1: Reproduction and Base Refactoring [checkpoint: 5472781]
Create a reproduction test case and implement the missing marker interaction logic in the `ComplexWidget` base class.

- [x] Task: Write Tests (Red Phase): Create a `pytest-qt` test in `tests/plugins/test_complex_markers.py` that adds a marker to a `ComplexRIWidget`, simulates a `mouseDragEvent` away from the trace, and verifies that the marker's visual position (during the drag) is NOT constrained to the trace. [5472781]
- [x] Task: Implement (Green Phase): Implement `_get_snapped_position`, `_on_marker_moving`, and refactor `_on_marker_dragged` in `ComplexWidget` (in `pyprobe/plugins/builtins/complex_plots.py`) to handle continuous snapping using the same logic as `WaveformWidget`. [5472781]
- [x] Task: Implement (Green Phase): Update `ComplexWidget._refresh_markers` to connect the `marker_moving` signal of `MarkerGlyph` to the new `_on_marker_moving` handler. [5472781]
- [x] Task: Write Tests: Verify the reproduction test now passes (marker remains on trace during drag). [5472781]
- [x] Task: Conductor - User Manual Verification 'Phase 1: Reproduction and Base Refactoring' (Protocol in workflow.md) [5472781]

## Phase 2: Verification Across Complex Lenses [checkpoint: 0c482dc]
Ensure the fix works correctly for all complex-data lenses, including those with secondary axes (Mag & Phase, FFT Mag & Angle).

- [x] Task: Write Tests: Add test cases for `ComplexMAWidget` (Mag & Phase) and `ComplexFftMagAngleWidget` to verify markers on both primary and secondary (phase) axes snap correctly while dragging. [0c482dc]
- [x] Task: Implement (if needed): Ensure `_get_snapped_position` in `ComplexWidget` correctly handles curves on the secondary axis (using `self._p2` if necessary, though `curve.getData()` should already provide the correct view coordinates). [0c482dc]
- [x] Task: Write Tests: Add test cases for `SingleCurveWidget` (used for Log Mag, Linear Mag, Phase (rad/deg)) to verify marker snapping. [0c482dc]
- [x] Task: Conductor - User Manual Verification 'Phase 2: Verification Across Complex Lenses' (Protocol in workflow.md) [0c482dc]

## Phase 3: Final Verification and Cleanup [checkpoint: c48c475]
Perform final checks and ensure no regressions.

- [x] Task: Write Tests: Verify that Constellation markers are still NOT constrained to a trace (as they are scatter points). [c48c475]
- [x] Task: Write Tests: Verify that real-valued Waveform markers still work correctly. [c48c475]
- [x] Task: Commit and finalize the track. [c48c475]
- [x] Task: Conductor - User Manual Verification 'Phase 3: Final Verification and Cleanup' (Protocol in workflow.md) [c48c475]
