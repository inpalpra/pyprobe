# Implementation Plan: Continuous Marker Trace Snapping

## Phase 1: Investigate and Refactor Marker Interaction Logic [checkpoint: d3da3d6]
- [x] Task: Analyze existing marker drag event handlers in `pyprobe/gui` or `pyprobe/plots` (e.g., `pyqtgraph.InfiniteLine` or custom marker classes) to understand the current "snap-on-release" behavior. [cedaccb]
- [x] Task: Refactor or introduce a unified marker event interface to allow intercepting the `mouseDragEvent` specifically for line/waveform traces. [cedaccb]
- [x] Task: Conductor - User Manual Verification 'Investigate and Refactor Marker Interaction Logic' (Protocol in workflow.md) - *Note: User is on CLI, verification must be strictly via automated test scripts.* [d3da3d6]

## Phase 2: Implement Continuous Snapping Core Logic [checkpoint: 3c50aab]
- [x] Task: Write Tests (Red Phase): Create extreme TDD headless `pytest-qt` tests verifying that dragging a marker on a waveform calculates the nearest point continuously. [584c2a2]
- [x] Task: Implement (Green Phase): Implement the core nearest-point calculation and snapping logic during the `mouseDragEvent`, ensuring it works for waveform plots but ignores constellation (scatter) plots. [584c2a2]
- [x] Task: Write Tests (Red Phase): Create tests verifying that the snapping calculation falls back gracefully or throttles if execution time exceeds a threshold (performance constraint). [584c2a2]
- [x] Task: Implement (Green Phase): Integrate throttling mechanisms (e.g., `QTimer` or frame-rate limiting) to ensure UI responsiveness on dense data. [584c2a2]
- [x] Task: Conductor - User Manual Verification 'Implement Continuous Snapping Core Logic' (Protocol in workflow.md) - *Note: User is on CLI, verify by running headless test scripts or demo scripts.* [3c50aab]

## Phase 3: Implement Smooth Interpolation [checkpoint: e9c0a19]
- [x] Task: Write Tests (Red Phase): Create `pytest-qt` tests verifying that when dragging between two discrete data indices, the marker position is interpolated linearly based on the mouse's X-coordinate. [8be1ea9]
- [x] Task: Implement (Green Phase): Enhance the snapping logic to calculate the exact fractional position between points (smooth interpolation) instead of rigidly jumping to the nearest integer index. [8be1ea9]
- [x] Task: Conductor - User Manual Verification 'Implement Smooth Interpolation' (Protocol in workflow.md) - *Note: User is on CLI, verify by running headless test scripts.* [e9c0a19]

## Phase 4: Integration and Edge Case Handling [checkpoint: d84433d]
- [x] Task: Write Tests (Red Phase): Create `pytest-qt` tests verifying edge cases: dragging off the ends of the trace, dragging vertically far away, and multi-trace snapping priority. [add937b]
- [x] Task: Implement (Green Phase): Finalize edge cases, ensuring the marker correctly tracks the horizontal position of the mouse relative to the trace's bounds. [8be1ea9]
- [x] Task: Conductor - User Manual Verification 'Integration and Edge Case Handling' (Protocol in workflow.md) - *Note: User is on CLI, verify by running headless test scripts or executing `./.venv/bin/python -m pyprobe examples/dsp_demo.py`.* [d84433d]
## Phase 5: Review Fixes
- [x] Task: Apply review suggestions [e29ebda]
