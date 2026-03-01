# Implementation Plan: Resolve GitHub CI E2E GUI Test Failure (Race Condition)

## Phase 1: CI Debug Infrastructure & Test Isolation
Fix the debug pipeline to enable rapid, isolated iteration on the failing E2E GUI tests.

- [ ] Task: Fix `.github/workflows/debug-targeted.yml` to support isolated E2E GUI test runs (e.g., via `inputs` for test files/patterns).
- [ ] Task: Create a minimal reproduction test case that simulates the `export_and_quit` sequence and fails deterministically on the GitHub runner.
- [ ] Task: Verify that the failing test is correctly isolated and captured by the fixed `debug-targeted.yml` pipeline.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: CI Debug Infrastructure & Test Isolation' (Protocol in workflow.md)

## Phase 2: Synchronous State Flushing Implementation
Research and implement a mechanism to synchronously flush the `WaveformWidget` and ensure all pending Qt events are processed before export.

- [ ] Task: Identify the optimal method (e.g., `qapp.processEvents()`, `widget.repaint()`, or explicit data synchronization) to flush the `WaveformWidget` state.
- [ ] Task: Implement a `flush_widget_events` utility in `pyprobe/gui/core` or a similar central location.
- [ ] Task: Integrate the `flush_widget_events` call into the `export_and_quit` logic to ensure data consistency between the `RedrawThrottler` buffer and the widget's internal state.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Synchronous State Flushing Implementation' (Protocol in workflow.md)

## Phase 3: Validation and Regression Testing
Verify the fix in the CI environment and ensure no regressions are introduced in the local development environment.

- [ ] Task: Write an E2E test specifically designed to detect data drift between the in-memory buffer and the exported widget image in a headless Xvfb environment.
- [ ] Task: Run the full E2E GUI test suite on the GitHub Actions Ubuntu runner using the fixed pipeline.
- [ ] Task: Perform a final verification in the local macOS environment to ensure no timing or performance regressions.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Validation and Regression Testing' (Protocol in workflow.md)
