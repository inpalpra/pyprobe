# Implementation Plan: Equation Editor

## Phase 1: Trace ID Management
Implement the logic to assign and manage unique `tr<n>` IDs for all probed variables.

- [x] Task: Implement `TraceIDManager` to handle ID allocation and reuse. eb7cba6
- [ ] Task: Integrate `TraceIDManager` with the probing system (likely in `pyprobe/core/` or `pyprobe/gui/`).
- [ ] Task: Ensure `tr<n>` IDs are displayed in the UI (Watch window and Plot legends).
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Trace ID Management' (Protocol in workflow.md)

## Phase 2: Equation Evaluation Engine
Implement the logic to parse and evaluate mathematical expressions using raw data.

- [ ] Task: Implement `EquationEngine` that takes an expression and a dictionary of raw data.
- [ ] Task: Support `numpy` and `scipy.signal` in the evaluation scope.
- [ ] Task: Implement dependency tracking (recursive equations).
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Equation Evaluation Engine' (Protocol in workflow.md)

## Phase 3: Equation Editor UI
Build the modal dialog for managing equations.

- [ ] Task: Create `EquationEditorDialog` using PyQt6.
- [ ] Task: Implement the "Add Equation" row logic.
- [ ] Task: Connect the UI to the `EquationEngine`.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Equation Editor UI' (Protocol in workflow.md)

## Phase 4: Plotting and Drag-and-Drop
Enable plotting equation results and dragging them into windows.

- [ ] Task: Implement `EquationPlotManager` to handle plotting `eq<n>` results.
- [ ] Task: Enable drag-and-drop from the `EquationEditorDialog` to plot windows.
- [ ] Task: Ensure real-time updates for equation plots.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Plotting and Drag-and-Drop' (Protocol in workflow.md)