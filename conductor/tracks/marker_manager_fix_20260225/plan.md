# Implementation Plan: Marker Manager Ref/Type Improvements

## Phase 1: Fix Reference Selection Bug
- [x] Task: Update `_update_existing_rows` in `MarkerManager` to synchronize the `enabled` state of the reference `QComboBox` based on the marker's type.
- [x] Task: Verify fix with reproduction script.

## Phase 2: Simplified Type Selection UI
- [x] Task: Create a `TypeToggleWidget` (or similar) that replaces the `QComboBox` for marker type.
    - Implementation: A segmented control with "Abs" and "Rel" buttons side-by-side, providing immediate visual state and one-click selection.
- [x] Task: Integrate `TypeToggleWidget` into `_populate_table` and `_update_existing_rows`.
- [x] Task: Ensure styling matches the theme and handles state changes.

## Phase 3: Final Verification [checkpoint: 8316f26]
- [x] Task: Run all tests in `tests/gui/test_marker_manager.py`.
- [x] Task: Perform manual verification of marker relativity functionality.
- [x] Task: Conductor - User Manual Verification 'Marker Manager Improvements' (Protocol in workflow.md)
