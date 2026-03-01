# Implementation Plan: Fix Downsampling and Zoom Reset Bugs

This plan addresses regressions in `WaveformWidget` downsampling logic and `AxisController` zoom reset behavior, verified against existing bug reports.

## Phase 1: Fix Responsive Downsampling (Visible Points Threshold)
Goal: Ensure raw data is shown when zoomed into a range with <= `MAX_DISPLAY_POINTS`.

- [ ] Task: Confirm current failure of `tests/gui/test_downsample_bug.py::test_zoom_in_shows_raw_data`
- [ ] Task: Implement fix in `pyprobe/plugins/builtins/waveform.py` to check visible range vs `MAX_DISPLAY_POINTS`
- [ ] Task: Verify fix with `tests/gui/test_downsample_bug.py::test_zoom_in_shows_raw_data`
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Responsive Downsampling' (Protocol in workflow.md)

## Phase 2: Fix Range-Aware Downsampling (Offset Bug)
Goal: Ensure downsampled data respects the current horizontal view range offset.

- [ ] Task: Confirm current failure of `tests/gui/test_downsample_bug.py::test_intermediate_zoom_redownsamples`
- [ ] Task: Update `pyprobe/plugins/builtins/waveform.py` to use the current view range when slicing data for downsampling
- [ ] Task: Verify fix with `tests/gui/test_downsample_bug.py::test_intermediate_zoom_redownsamples`
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Range-Aware Downsampling' (Protocol in workflow.md)

## Phase 3: Fix Zoom Reset Drift
Goal: Prevent view range drift after calling `AxisController.reset()`.

- [ ] Task: Confirm current failure of `tests/gui/test_reset_zoom_bug.py::test_reset_view_range_does_not_drift`
- [ ] Task: Modify `pyprobe/core/axis_controller.py` to cancel ongoing animations and ensure state consistency during `reset()`
- [ ] Task: Verify fix with `tests/gui/test_reset_zoom_bug.py::test_reset_view_range_does_not_drift`
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Zoom Reset Stability' (Protocol in workflow.md)

## Phase 4: Final Verification and CI Validation
Goal: Ensure all fixes work together and pass on CI (Ubuntu).

- [ ] Task: Run full local suite `tests/gui/test_downsample_bug.py` and `tests/gui/test_reset_zoom_bug.py`
- [ ] Task: Run CI verification using `gh workflow run test-only.yml` and monitor results
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Final Verification' (Protocol in workflow.md)