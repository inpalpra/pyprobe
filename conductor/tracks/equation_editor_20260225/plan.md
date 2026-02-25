# Implementation Plan: Equation Editor

## Phase 1: Trace ID Management
Implement the logic to assign and manage unique `tr<n>` IDs for all probed variables.

- [x] Task: Implement `TraceIDManager` to handle ID allocation and reuse. eb7cba6
- [x] Task: Integrate `TraceIDManager` with the probing system. 5e9b8a3
- [x] Task: Ensure `tr<n>` IDs are displayed in the UI (Watch window and Plot legends). 5e9b8a3
- [x] Task: Conductor - User Manual Verification 'Phase 1: Trace ID Management' (Protocol in workflow.md)

## Phase 2: Equation Evaluation Engine
Implement the logic to parse and evaluate mathematical expressions using raw data.

- [x] Task: Implement `EquationEngine` that takes an expression and a dictionary of raw data. 3f9a7b1
- [x] Task: Support `numpy` and `scipy.signal` in the evaluation scope. 3f9a7b1
- [x] Task: Implement dependency tracking (recursive equations). 3f9a7b1
- [x] Task: Conductor - User Manual Verification 'Phase 2: Equation Evaluation Engine' (Protocol in workflow.md)

## Phase 3: Equation Editor UI
Build the modal dialog for managing equations.

- [x] Task: Create `EquationEditorDialog` using PyQt6. 5f7a9b2
- [x] Task: Implement the "Add Equation" row logic. 5f7a9b2
- [x] Task: Connect the UI to the `EquationEngine`. 5f7a9b2
- [x] Task: Conductor - User Manual Verification 'Phase 3: Equation Editor UI' (Protocol in workflow.md)

## Phase 4: Plotting and Drag-and-Drop
Enable plotting equation results and dragging them into windows.

- [x] Task: Implement `EquationPlotManager` to handle plotting `eq<n>` results. 7a8b9c0
- [x] Task: Enable drag-and-drop from the `EquationEditorDialog` to plot windows. 7a8b9c0
- [x] Task: Ensure real-time updates for equation plots. 7a8b9c0
- [x] Task: Conductor - User Manual Verification 'Phase 4: Plotting and Drag-and-Drop' (Protocol in workflow.md)