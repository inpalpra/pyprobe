# Specification: Fix Downsampling and Zoom Reset Bugs

## Overview
This track addresses three regressions in the waveform plotting logic:
1. Downsampling remains active even when zooming into a small range that should show raw data.
2. Downsampled data always starts from index 0, ignoring the current view range.
3. Resetting the view range causes drift, likely due to uncancelled animations or incorrect state management in `AxisController`.

## Functional Requirements
- **Responsive Downsampling:** When the number of samples in the current view range is less than or equal to `MAX_DISPLAY_POINTS`, the waveform should display raw data.
- **Range-Aware Downsampling:** When downsampling is active, it must only process and display the data within (or slightly beyond) the current horizontal view range.
- **Stable Reset:** The `AxisController.reset()` method must immediately stop all view animations and restore the range to the full data extent without subsequent drifting.

## Acceptance Criteria
- `tests/gui/test_downsample_bug.py::test_zoom_in_shows_raw_data` passes.
- `tests/gui/test_downsample_bug.py::test_intermediate_zoom_redownsamples` passes.
- `tests/gui/test_reset_zoom_bug.py::test_reset_view_range_does_not_drift` passes.
- No regressions in other GUI tests.

## Out of Scope
- Major refactoring of the `WaveformWidget` or `AxisController`.
- Changes to other plugins unless they share the same buggy logic.