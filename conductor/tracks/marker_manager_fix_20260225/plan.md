# Implementation Plan: Marker Manager Ref/Type Improvements

## Phase 1: Fix Reference Selection Bug
- [ ] Task: Update `_update_existing_rows` in `MarkerManager` to synchronize the `enabled` state of the reference `QComboBox` based on the marker's type.
- [ ] Task: Verify fix with reproduction script.

## Phase 2: Simplified Type Selection UI
- [ ] Task: Create a `TypeToggleWidget` (or similar) that replaces the `QComboBox` for marker type.
    - Implementation: A segmented control with "Abs" and "Rel" buttons side-by-side, providing immediate visual state and one-click selection.
- [ ] Task: Integrate `TypeToggleWidget` into `_populate_table` and `_update_existing_rows`.
- [ ] Task: Ensure styling matches the theme and handles state changes.

## Phase 3: Final Verification
- [ ] Task: Run all tests in `tests/gui/test_marker_manager.py`.
- [ ] Task: Perform manual verification of marker relativity functionality.
- [ ] Task: Conductor - User Manual Verification 'Marker Manager Improvements' (Protocol in workflow.md)
