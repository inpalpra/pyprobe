# Implementation Plan: Continuous Marker Trace Snapping

## Phase 1: Investigate and Refactor Marker Interaction Logic [checkpoint: d3da3d6]
- [x] Task: Analyze existing marker drag event handlers in `pyprobe/gui` or `pyprobe/plots` (e.g., `pyqtgraph.InfiniteLine` or custom marker classes) to understand the current "snap-on-release" behavior. [cedaccb]
- [x] Task: Refactor or introduce a unified marker event interface to allow intercepting the `mouseDragEvent` specifically for line/waveform traces. [cedaccb]
- [x] Task: Conductor - User Manual Verification 'Investigate and Refactor Marker Interaction Logic' (Protocol in workflow.md) - *Note: User is on CLI, verification must be strictly via automated test scripts.* [d3da3d6]

## Phase 2: Implement Continuous Snapping Core Logic
- [ ] Task: Write Tests (Red Phase): Create extreme TDD headless `pytest-qt` tests verifying that dragging a marker on a waveform calculates the nearest point continuously.
- [ ] Task: Implement (Green Phase): Implement the core nearest-point calculation and snapping logic during the `mouseDragEvent`, ensuring it works for waveform plots but ignores constellation (scatter) plots.
- [ ] Task: Write Tests (Red Phase): Create tests verifying that the snapping calculation falls back gracefully or throttles if execution time exceeds a threshold (performance constraint).
- [ ] Task: Implement (Green Phase): Integrate throttling mechanisms (e.g., `QTimer` or frame-rate limiting) to ensure UI responsiveness on dense data.
- [ ] Task: Conductor - User Manual Verification 'Implement Continuous Snapping Core Logic' (Protocol in workflow.md) - *Note: User is on CLI, verify by running headless test scripts or demo scripts.*

## Phase 3: Implement Smooth Interpolation
- [ ] Task: Write Tests (Red Phase): Create `pytest-qt` tests verifying that when dragging between two discrete data indices, the marker position is interpolated linearly based on the mouse's X-coordinate.
- [ ] Task: Implement (Green Phase): Enhance the snapping logic to calculate the exact fractional position between points (smooth interpolation) instead of rigidly jumping to the nearest integer index.
- [ ] Task: Conductor - User Manual Verification 'Implement Smooth Interpolation' (Protocol in workflow.md) - *Note: User is on CLI, verify by running headless test scripts.*

## Phase 4: Integration and Edge Case Handling
- [ ] Task: Write Tests (Red Phase): Create `pytest-qt` tests verifying edge cases: dragging off the ends of the trace, dragging vertically far away, and multi-trace snapping priority.
- [ ] Task: Implement (Green Phase): Finalize edge cases, ensuring the marker correctly tracks the horizontal position of the mouse relative to the trace's bounds.
- [ ] Task: Conductor - User Manual Verification 'Integration and Edge Case Handling' (Protocol in workflow.md) - *Note: User is on CLI, verify by running headless test scripts or executing `./.venv/bin/python -m pyprobe examples/dsp_demo.py`.*