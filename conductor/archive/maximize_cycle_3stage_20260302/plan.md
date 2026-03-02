# Implementation Plan - 3-Stage Maximization Cycle

## Phase 1: Infrastructure and State Management
Update `LayoutManager` to support three maximization states and provide the necessary signaling for `MainWindow` to react.

- [ ] **Task 1: Update `LayoutManager` State Machine**
    - [ ] Define `MaximizeState` enum: `NORMAL`, `CONTAINER`, `FULL`.
    - [ ] Update `LayoutManager` to track the current state.
    - [ ] Update `toggle_maximize` logic to cycle: `NORMAL` -> `CONTAINER` -> `FULL` -> `NORMAL`.
    - [ ] Add `full_maximize_toggled(bool)` signal to `LayoutManager`.
- [ ] **Task 2: TDD - `LayoutManager` Unit Tests**
    - [ ] Write tests in `tests/test_layout_manager.py` verifying the 3-stage cycle.
    - [ ] Verify that `full_maximize_toggled` signal emits correctly.
- [ ] **Task 3: Conductor - User Manual Verification 'Phase 1: Infrastructure and State Management' (Protocol in workflow.md)**

## Phase 2: MainWindow Integration and UI Toggling
Modify `MainWindow` to respond to the `full_maximize_toggled` signal and manage the visibility of non-graph widgets.

- [ ] **Task 1: Track UI Visibility State in `MainWindow`**
    - [ ] Add logic to save the visibility of `FileTree`, `ScalarWatchSidebar`, `CodeViewer`, and `ControlBar` before entering `FULL` mode.
- [ ] **Task 2: Implement UI Toggling in `MainWindow`**
    - [ ] Connect `lm.full_maximize_toggled` to a new `_on_full_maximize_toggled` slot.
    - [ ] In `FULL` mode: Hide UI components, update Status Bar message.
    - [ ] On exit: Restore UI components using saved visibility states.
- [ ] **Task 3: TDD - `MainWindow` Maximization Tests**
    - [ ] Write integration tests verifying that widgets hide/show correctly during the cycle.
    - [ ] Verify that RHS coordinate display remains functional in `FULL` mode.
- [ ] **Task 4: Conductor - User Manual Verification 'Phase 2: MainWindow Integration and UI Toggling' (Protocol in workflow.md)**

## Phase 3: Final Polishing and Regression Testing
Ensure the cycle is robust and handles manual sidebar toggling correctly.

- [ ] **Task 1: Handle Manual UI Toggling during Cycle**
    - [ ] Ensure that if a user manually shows/hides a sidebar in Stage 2, the restoration logic correctly accounts for it (or defines clear behavior).
- [ ] **Task 2: Full Regression Suite Execution**
    - [ ] Run all GUI tests to ensure no regressions in plot rendering or interaction.
- [ ] **Task 3: Conductor - User Manual Verification 'Phase 3: Final Polishing and Regression Testing' (Protocol in workflow.md)**
