# Specification: Continuous Marker Trace Snapping

## Overview
This feature enhances the UX of marker interactions in PyProbe Plots. Currently, when dragging a marker, it follows the mouse freely and only snaps back to the trace upon mouse release. This track modifies the behavior so that the marker remains continuously "glued" to the trace it belongs to during the active drag operation.

## Functional Requirements
- **Continuous Snapping:** During a mouse drag event on a marker, the marker must continuously calculate and snap to the nearest point on its associated trace, rather than following the free mouse cursor.
- **Plot Scope:** This behavior applies universally to all plot types *except* constellation plots (scatter plots). Constellation plots will retain their existing marker behavior.
- **Interpolation:** While dragging, the marker should interpolate smoothly between discrete data points on the trace to provide fluid visual feedback, rather than jumping rigidly from index to index.
- **Performance Throttling:** The continuous snapping calculation must not degrade UI performance unacceptably on dense traces. If necessary, intermediate snapping calculations should be throttled or optimized to ensure the drag operation remains smooth and responsive to the user's mouse movements.

## Non-Functional Requirements
- **Performance:** Dragging a marker must remain visually smooth, degrading gracefully via throttling if computation takes too long on dense datasets.

## Acceptance Criteria
- [ ] Dragging a marker on a standard waveform plot keeps the marker firmly on the trace line during the entire drag operation.
- [ ] Dragging a marker on a standard waveform plot shows smooth interpolation between points rather than discrete jumps.
- [ ] Attempting to drag the mouse far away from the trace vertically still causes the marker to track the horizontal position on the trace.
- [ ] The feature does not apply to or break markers on constellation plots.
- [ ] Performance remains acceptable (smooth drag) even on high-density data arrays, utilizing throttling if necessary.

## Out of Scope
- Adding new types of markers.
- Modifying the visual appearance of the markers themselves.