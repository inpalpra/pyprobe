# Specification: Marker Persistence Across View/Lens Switches

## Overview
Currently, markers in PyProbe are transient and tied to the lifecycle of the active plot widget. When a user switches between views (e.g., from Waveform to FFT Mag), the old plot widget is often destroyed or cleared, and its markers are lost. This track aims to implement a persistence mechanism that ensures markers are saved per-view and restored when the user returns to that view.

## Functional Requirements
1. **Per-View Persistence:**
   - Markers must be associated with the specific plugin/view type (e.g., `Waveform`, `FFT Mag`, `Constellation`) that created them.
   - When switching away from a view, its markers must be "parked" or saved in a non-volatile state within the application's session.
   - When switching back to a view, its specific markers must be re-instantiated and rendered.

2. **Global Unique Marker IDs:**
   - Marker IDs (e.g., `m0`, `m1`) must be unique across the entire project, regardless of which view they belong to.
   - If `m0` is created in Waveform view, the next marker created in FFT view must be `m1`, even if `m0` is not currently visible.

3. **Marker Manager Filtering:**
   - The Marker Manager table must filter its display to only show markers belonging to the currently active view.
   - The underlying data structure in the Marker Manager must still maintain all markers (for all views) to ensure ID uniqueness and global state management.

4. **Project State Persistence:**
   - Markers must be serialized into the project's state file (if applicable) or a session configuration file so they can be restored when the application is restarted.

## Non-Functional Requirements
- **Performance:** Switching views should not be perceptibly slowed down by the marker restoration logic.
- **UI Consistency:** The transition of markers should feel seamless to the user.

## Acceptance Criteria
- [ ] User creates markers `m0`, `m1` in Waveform view.
- [ ] User switches to FFT view; `m0`, `m1` are no longer visible.
- [ ] User creates marker `m2` in FFT view.
- [ ] User switches back to Waveform view; `m0`, `m1` are restored, `m2` is hidden.
- [ ] Marker Manager correctly shows only `m0`, `m1` while in Waveform view, and only `m2` while in FFT view.
- [ ] Closing and reopening the application with the same data restores the markers in their respective views.

## Out of Scope
- Mapping markers between views (e.g., a time-domain marker appearing at a specific frequency in FFT).
- Cross-view marker relationships (e.g., `m0` in Waveform being relative to `m1` in FFT).
