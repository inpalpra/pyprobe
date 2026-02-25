# Specification: Marker Manager Reference Selection and Type UI Polish

## Overview
This track addresses two issues in the Marker Manager (Detailed View):
1. A bug where the reference marker selection (currently showing "None") is unresponsive or fails to display a list of available markers when a marker is set to "Relative" type.
2. A UI enhancement to simplify the "Absolute/Relative" type selection by removing unnecessary menu nesting/arrows and making options more immediate.

## Functional Requirements
- **Reference Selection Fix:**
    - When a marker's type is "Relative", clicking the reference column (initially "None") must present a list of all *other* available markers.
    - Selecting a marker from this list must correctly update the reference and recalculate the relative position.
- **Type Selection UI:**
    - Replace the current Absolute/Relative selection mechanism with a "Simplified Menu" (side-by-side toggle buttons) that eliminates unnecessary arrows or nested clicks.
    - Ensure the options "Absolute" and "Relative" are immediately accessible.

## Non-Functional Requirements
- Maintain performance in the Marker Manager table.
- Consistent styling with the existing PyQt6/pyqtgraph theme.

## Acceptance Criteria
- [ ] Clicking "None" (or the current reference) for a Relative marker opens a selection menu with all other markers.
- [ ] Choosing a reference marker successfully links the two markers.
- [ ] The "Type" selection no longer has an unnecessary arrow/sub-menu and feels "immediate".
- [ ] No regression in basic marker creation, movement, or deletion.

## Out of Scope
- Global marker settings (colors, default types).
- Marker snapping or advanced math operations beyond basic relativity.
