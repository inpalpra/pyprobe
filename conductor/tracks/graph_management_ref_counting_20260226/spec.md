# Specification: Graph Window Management and Trace Reference Counting

## Overview
This track addresses critical bugs in the Equation Editor's plotting logic and introduces a formal architecture for managing graph windows and their contained traces. It implements a reference-counting mechanism to ensure that variables are only "probed" as long as they are active in at least one graph window.

## Functional Requirements
- **Graph Window Management:**
    - Use globally unique nomenclature `w0, w1, w2, ...` for graph windows.
    - Implement a 'Close' button (X) on all graph windows to allow permanent removal.
    - Prevent the creation of empty/broken windows from the Equation Editor.
- **Trace Management (Unprobing):**
    - Users can remove a specific trace from a window via:
        - An 'X' icon in the plot legend.
        - A right-click context menu on the trace/legend.
    - **Reference Counting:**
        - Track how many windows refer to a specific trace (variable or equation).
        - When the reference count for a trace reaches zero (e.g., all windows containing it are closed or the trace is removed from them), the trace is automatically "unprobed".
        - "Unprobing" means:
            - Removing the variable from the underlying probe engine.
            - Removing the highlight and "eye" icon from the code gutter.
            - Freeing the associated color in the `ColorManager`.
- **Equation Editor Fixes:**
    - Fix the bug where clicking "Plot" multiple times creates empty, unremovable windows.
    - Ensure equations correctly render data upon creation and re-run.

## Non-Functional Requirements
- **Performance:** Reference counting and window lifecycle management should not introduce perceptible lag in the UI.
- **UI Consistency:** The close buttons and context menus should follow the existing style.

## Acceptance Criteria
- Clicking "Plot" in the Equation Editor creates a functional window with a unique ID (e.g., `w0`).
- Closing a window removes it from the layout and reduces the ref count for all its traces.
- Removing the last instance of a trace (via legend 'X' or closing the window) unhighlights the code and removes the gutter icon.
- No "ghost" windows or empty panes remain after removal.

## Out of Scope
- Persistent storage of window layouts (to be handled in a future track).
