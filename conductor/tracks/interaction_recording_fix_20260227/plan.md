# Implementation Plan: Comprehensive Interaction Recording Fix

This plan addresses several missing or incorrect user interaction recordings in the PyProbe StepRecorder system.

## Phase 1: Research and Reproduction
Create reproduction scripts and tests to confirm the reported issues.

- [x] Task: Create a reproduction script (`reproduce_recording_issues.py`) that uses `StepRecorder` and simulates the problematic interactions (Run/Pause click, Lens change, Equation edit, Legend toggle).
- [x] Task: Write Tests: Create a unit test in `tests/report/test_step_recorder_integration.py` that asserts the correct string is recorded for each interaction.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Research and Reproduction' (Protocol in workflow.md)

## Phase 2: Fixing Execution Control and Equation Recording
Resolve the incorrect "Clicked Pause" labeling and add missing equation edit tracking.

- [x] Task: Implement Feature: Refactor `ControlBar._on_action_clicked` to capture the button text *before* any state transitions occur, ensuring `action_clicked_with_state` carries the correct label.
- [x] Task: Implement Feature: Add `equation_edited` signal to `EquationEditorDialog` (emitted when `QLineEdit` text changes) and wire it to `StepRecorder` in `MainWindow`.
- [x] Task: Write Tests: Verify that clicking "Run" records "Clicked Run" and editing an equation records "Edited equation: eq<n>".
- [x] Task: Conductor - User Manual Verification 'Phase 2: Fixing Execution Control and Equation Recording' (Protocol in workflow.md)

## Phase 3: Fixing Lens Change Recording
Investigate and resolve why `panel_lens_changed` is occasionally missed.

- [x] Task: Analyze `ProbeController` and `MainWindow` to ensure `panel_lens_changed` is correctly emitted and recorded for all lens types, including complex Mag/Phase lenses.
- [x] Task: Implement Feature: Ensure `anchor.identity_label()` used in the recording string is consistent and descriptive.
- [x] Task: Write Tests: Verify that changing lenses on various data types results in correctly formatted steps in the recorder.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Fixing Lens Change Recording' (Protocol in workflow.md)

## Phase 4: Implementing Legend Visibility Toggle Recording
Add the ability to record when a user toggles trace visibility in multi-trace windows.

- [x] Task: Implement Feature: Enhance `RemovableLegendItem` to detect single clicks on the "little horizontal line" (color swatch).
- [x] Task: Implement Feature: Add `trace_visibility_changed` signal to `RemovableLegendItem` and forward it through `ProbePanel` and `ProbeController`.
- [x] Task: Implement Feature: Wire the new signal to `StepRecorder` in `MainWindow`.
- [x] Task: Write Tests: Verify that clicking the legend swatch for an overlaid trace records "Toggled visibility of <Trace Name> in window w<n>".
- [x] Task: Conductor - User Manual Verification 'Phase 4: Implementing Legend Visibility Toggle Recording' (Protocol in workflow.md)

## Phase 5: Final Verification
Ensure all fixes work together and meet the forensic-grade reproducibility goal.

- [x] Task: Run the full test suite (`pytest`) to ensure no regressions in the reporting or plotting systems.
- [x] Task: Perform a manual end-to-end test: Record a session with all target interactions, generate a bug report, and verify the "Steps to Reproduce" are perfect.
- [x] Task: Conductor - User Manual Verification 'Phase 5: Final Verification' (Protocol in workflow.md)
