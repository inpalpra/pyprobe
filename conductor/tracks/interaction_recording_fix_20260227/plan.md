# Implementation Plan: Comprehensive Interaction Recording Fix

This plan addresses several missing or incorrect user interaction recordings in the PyProbe StepRecorder system.

## Phase 1: Research and Reproduction
Create reproduction scripts and tests to confirm the reported issues.

- [ ] Task: Create a reproduction script (`reproduce_recording_issues.py`) that uses `StepRecorder` and simulates the problematic interactions (Run/Pause click, Lens change, Equation edit, Legend toggle).
- [ ] Task: Write Tests: Create a unit test in `tests/report/test_step_recorder_integration.py` that asserts the correct string is recorded for each interaction.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Research and Reproduction' (Protocol in workflow.md)

## Phase 2: Fixing Execution Control and Equation Recording
Resolve the incorrect "Clicked Pause" labeling and add missing equation edit tracking.

- [ ] Task: Implement Feature: Refactor `ControlBar._on_action_clicked` to capture the button text *before* any state transitions occur, ensuring `action_clicked_with_state` carries the correct label.
- [ ] Task: Implement Feature: Add `equation_edited` signal to `EquationEditorDialog` (emitted when `QLineEdit` text changes) and wire it to `StepRecorder` in `MainWindow`.
- [ ] Task: Write Tests: Verify that clicking "Run" records "Clicked Run" and editing an equation records "Edited equation: eq<n>".
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Fixing Execution Control and Equation Recording' (Protocol in workflow.md)

## Phase 3: Fixing Lens Change Recording
Investigate and resolve why `panel_lens_changed` is occasionally missed.

- [ ] Task: Analyze `ProbeController` and `MainWindow` to ensure `panel_lens_changed` is correctly emitted and recorded for all lens types, including complex Mag/Phase lenses.
- [ ] Task: Implement Feature: Ensure `anchor.identity_label()` used in the recording string is consistent and descriptive.
- [ ] Task: Write Tests: Verify that changing lenses on various data types results in correctly formatted steps in the recorder.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Fixing Lens Change Recording' (Protocol in workflow.md)

## Phase 4: Implementing Legend Visibility Toggle Recording
Add the ability to record when a user toggles trace visibility in multi-trace windows.

- [ ] Task: Implement Feature: Enhance `RemovableLegendItem` to detect single clicks on the "little horizontal line" (color swatch).
- [ ] Task: Implement Feature: Add `trace_visibility_changed` signal to `RemovableLegendItem` and forward it through `ProbePanel` and `ProbeController`.
- [ ] Task: Implement Feature: Wire the new signal to `StepRecorder` in `MainWindow`.
- [ ] Task: Write Tests: Verify that clicking the legend swatch for an overlaid trace records "Toggled visibility of <Trace Name> in window w<n>".
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Implementing Legend Visibility Toggle Recording' (Protocol in workflow.md)

## Phase 5: Final Verification
Ensure all fixes work together and meet the forensic-grade reproducibility goal.

- [ ] Task: Run the full test suite (`pytest`) to ensure no regressions in the reporting or plotting systems.
- [ ] Task: Perform a manual end-to-end test: Record a session with all target interactions, generate a bug report, and verify the "Steps to Reproduce" are perfect.
- [ ] Task: Conductor - User Manual Verification 'Phase 5: Final Verification' (Protocol in workflow.md)
