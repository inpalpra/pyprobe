# Implementation Plan: Graph Window Management and Trace Reference Counting

## Phase 1: Window ID and Reference Counting Core
Establish the underlying data structures to track windows and their trace dependencies.

- [x] Task: Implement `WindowIDManager` to provide globally unique `w0, w1, ...` IDs. 0041d11
- [x] Task: Implement `TraceReferenceManager` to track which windows are using which `tr<n>` or `eq<n>` IDs. 2198fba
- [x] Task: Write Tests: Verify that `TraceReferenceManager` correctly increments/decrements counts and triggers a "cleanup" signal when a count hits zero. 2198fba
- [x] Task: Conductor - User Manual Verification 'Phase 1: Window ID and Reference Counting Core' (Protocol in workflow.md) a79198d

## Phase 2: Graph Window Lifecycle (Creation & Destruction)
Integrate the new window management into the UI and implement the "Close" functionality.

- [ ] Task: Update `LayoutManager` to assign `WindowID` to all new plot windows.
- [ ] Task: Add a 'Close' button (X) to the `PlotWidget` header/container.
- [ ] Task: Implement `PlotWidget.close_window()` which removes itself from the layout and notifies `TraceReferenceManager`.
- [ ] Task: Write Tests: Verify that closing a window correctly removes it from the UI and reduces reference counts for all contained traces.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Graph Window Lifecycle' (Protocol in workflow.md)

## Phase 3: Trace Removal (Unprobing) UI
Enable users to remove specific traces without closing the entire window.

- [ ] Task: Update `LegendItem` or `PlotLegend` to include an 'X' button for each trace.
- [ ] Task: Add a "Remove Trace" option to the plot context menu.
- [ ] Task: Write Tests: Verify that removing a trace via the legend correctly updates the window and the reference manager.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Trace Removal (Unprobing) UI' (Protocol in workflow.md)

## Phase 4: Equation Editor Fixes
Resolve the bugs related to empty plots and redundant windows in the Equation Editor.

- [ ] Task: Debug and fix the race condition causing empty plots in the Equation Editor.
- [ ] Task: Refactor Equation Editor's "Plot" button to use the new `LayoutManager` window creation flow.
- [ ] Task: Write Tests: Verify that clicking "Plot" in the Equation Editor creates a populated window and that re-running the equation updates the plot.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Equation Editor Fixes' (Protocol in workflow.md)

## Phase 5: Global Unprobing Integration
Connect the reference manager to the rest of the application (Code Viewer, Probe Engine).

- [ ] Task: Integrate `TraceReferenceManager` with the `CodeViewer` to remove highlights and "eye" icons when a trace is no longer referenced.
- [ ] Task: Ensure the `ProbeEngine` stops collecting data for traces with zero references.
- [ ] Task: Write Tests: E2E test verifying that dragging a variable to a plot, then removing it, correctly cleans up the code viewer highlights.
- [ ] Task: Conductor - User Manual Verification 'Phase 5: Global Unprobing Integration' (Protocol in workflow.md)
