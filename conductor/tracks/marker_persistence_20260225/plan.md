# Implementation Plan: Marker Persistence Across View/Lens Switches

This plan outlines the steps to implement persistent markers that survive view/lens switches in PyProbe, ensuring they are saved per-view and restored correctly.

## Phase 1: Research and Core Infrastructure
Analyze the current marker management system and implement the necessary foundations for global ID uniqueness and per-view tracking.

- [ ] Task: Analyze `MarkerManager`, `PluginRegistry`, and `PlotWidget` in `pyprobe/gui` and `pyprobe/plots` to understand how markers are currently created, stored, and destroyed during view switches.
- [ ] Task: Write Tests: Verify that `MarkerManager` (or a new centralized registry) can track marker IDs across multiple plugins without collisions.
- [ ] Task: Implement Feature: Refactor marker creation logic to use a centralized ID generator that guarantees global uniqueness across the entire session.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Research and Core Infrastructure' (Protocol in workflow.md)

## Phase 2: Per-View Persistence and Switching Logic
Implement the logic to "park" markers when a view is hidden and restore them when it becomes active again.

- [ ] Task: Write Tests: Create a headless GUI test that adds markers to a `WaveformPlot`, simulates a switch to another plugin, and verifies that the markers are still available in memory but not rendered on the new plot.
- [ ] Task: Implement Feature: Modify the `PlotController` or `LayoutManager` to capture a view's markers before destruction/hiding and re-inject them when the view is re-created/shown.
- [ ] Task: Write Tests: Verify that switching back to a previous view correctly re-renders all its original markers with their original properties (position, color, type).
- [ ] Task: Implement Feature: Ensure `PlotWidget` cleanup logic does not purge markers intended for persistence.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Per-View Persistence and Switching Logic' (Protocol in workflow.md)

## Phase 3: Marker Manager UI Filtering
Update the Marker Manager table to only display markers relevant to the currently active plot view.

- [ ] Task: Write Tests: Verify that the `MarkerManager` model filters markers based on an "active view" property.
- [ ] Task: Implement Feature: Add a filtering mechanism to the `MarkerManager` table view that updates dynamically when the active plugin changes.
- [ ] Task: Write Tests: Ensure that creating a new marker in the active view correctly updates the filtered table immediately.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Marker Manager UI Filtering' (Protocol in workflow.md)

## Phase 4: Serialization and Project State
Ensure markers are saved to the project configuration and restored across application restarts.

- [ ] Task: Write Tests: Verify that markers (with their view associations and properties) can be serialized to JSON and deserialized back into active markers.
- [ ] Task: Implement Feature: Update the PyProbe state persistence logic to include the global marker registry.
- [ ] Task: Write Tests: Perform an E2E test verifying that markers created in one session are restored in their respective views in a new session.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Serialization and Project State' (Protocol in workflow.md)
