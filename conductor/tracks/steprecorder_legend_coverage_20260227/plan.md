# Implementation Plan: Legend trace toggles StepRecorder coverage

## Phase 1: Research & Failing Tests (Red Phase)
- [x] Task: Locate where legend entries are created and clicked in `pyqtgraph` or the PyProbe GUI.
- [x] Task: Create a new test file `tests/gui/test_report_bug_legend_toggle.py`.
- [x] Task: Write failing test: `test_legend_toggle_records_step` (Start recording, simulate legend toggle, assert step recorded).
- [x] Task: Write failing test: `test_legend_toggle_records_once_per_click` (Assert exactly one step per user action).
- [x] Task: Write failing test: `test_legend_toggle_not_recorded_when_not_recording` (Emit signal, assert no step).
- [x] Task: Write failing test: `test_lens_switch_does_not_emit_toggle_event` (Simulate lens switch, assert no visibility toggle step).
- [x] Task: Write failing test: `test_toggle_message_contains_window_id_and_anchor` (Verify the exact message format).
- [x] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

## Phase 2: Signal Introduction & Wiring (Green Phase)
- [x] Task: If not present, introduce `legend_trace_toggled(str, bool)` signal in the relevant Plot panel/item.
- [x] Task: Ensure the signal is emitted correctly in response to user legend clicks.
- [x] Task: In `MainWindow._show_report_bug_dialog()`, wire the signal to the `StepRecorder`.
- [x] Task: Verify that all tests in `tests/gui/test_report_bug_legend_toggle.py` pass.
- [x] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

## Phase 3: Regression & Final Cleanup
- [x] Task: Run full regression suite (`uv run pytest`) to ensure no regressions.
- [x] Task: Verify code coverage for the new feature.
- [x] Task: Final code review and documentation update (if any).
- [x] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)

## Phase 4: Post-Implementation Fixes (Re-verification)
- [x] Task: Fix coordinate mapping bug in `RemovableLegendItem.mouseClickEvent` and `mouseDoubleClickEvent`.
- [x] Task: Ensure `ComplexRIWidget` and `ComplexFftMagAngleWidget` add all curves to the legend.
- [x] Task: Re-verify with mouse simulation test.
- [x] Task: Conductor - User Manual Verification 'Phase 4' (Protocol in workflow.md)

## Phase 5: Fix Native pyqtgraph Event Bubbling for Legend Clicks
- [x] Task: Diagnose that `ItemSample.mouseClickEvent` natively toggles visibility, thus bypassing `RemovableLegendItem.mouseClickEvent`.
- [x] Task: Connect `LegendItem.sigSampleClicked` to a new `_on_sample_clicked` handler in `RemovableLegendItem` to correctly emit `trace_visibility_changed`.
- [x] Task: Fix testing errors in `test_trace_removal.py` where mock coordinates triggered `TypeError`.
- [x] Task: Verify no regressions in GUI tests.
