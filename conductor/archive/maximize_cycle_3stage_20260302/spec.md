# Track: 3-Stage Maximization Cycle for Graph Widgets

## 1. Overview
The current "Maximize" behavior (triggered by the 'M' key) is a simple 2-stage toggle between "Normal" and "Maximized in Container". This track enhances it to a 3-stage cycle that allows a focused graph to occupy the entire application space, providing maximum forensic clarity by hiding non-graph widgets.

## 2. Functional Requirements

### 2.1 Cycle States
The 'M' key will cycle through the following three states:

1.  **State 1: Normal (Initial State)**
    -   Standard grid layout within the `ProbePanelContainer`.
    -   Sidebars (File Tree, Symbol Watch) and Code Viewer are visible if they were active.

2.  **State 2: Maximized in Container (First Press)**
    -   The focused graph fills the entire `ProbePanelContainer`.
    -   Other graph widgets are parked (hidden).
    -   Non-graph widgets (File Tree, Code Viewer, etc.) remain visible in their current positions.
    -   *Existing behavior already supports this.*

3.  **State 3: Maximized Full (Second Press)**
    -   The focused graph fills the entire application window space.
    -   The following widgets are hidden:
        -   Code Viewer
        -   Symbol Watch (Scalar Watch Sidebar)
        -   File Tree (Explorer pane)
        -   Control Bar (Run/Pause/Stop/Open)
    -   The **Status Bar** at the bottom remains visible.
    -   The Status Bar should display a persistent message (e.g., in the message area): "Press 'M' to restore layout."
    -   The **RHS coordinate display** (X/Y) on the Status Bar must remain visible and functional.
    -   *New behavior.*

4.  **State 4: Restore to Normal (Third Press)**
    -   All graphs and non-graph widgets are restored to their states prior to the start of the maximization sequence.
    -   Visibility and size of non-graph widgets are preserved based on their `is_expanded` or visibility status *before* State 1.

### 2.2 Navigation
-   The cycle is strictly controlled by the 'M' key.
-   Escape key remains assigned to its current workflows (e.g., exiting tool modes) and does NOT trigger restoration.

### 2.3 Layout Logic
-   The system must track the visibility and "expanded" state of `CollapsiblePane` (File Tree, Watch Pane) and `CodeViewer` to ensure perfect restoration.

## 3. Non-Functional Requirements
-   **Instant Transitions:** Transitions between states must be instant (no animation requested).
-   **State Integrity:** Hidden graphs must continue to receive and process data in the background.

## 4. Acceptance Criteria
-   [ ] Pressing 'M' on a focused graph fills the container and hides other graphs.
-   [ ] Pressing 'M' again hides the Code Viewer, File Tree, Symbol Watch, and Control Bar, expanding the graph to the full window.
-   [ ] Pressing 'M' a third time restores the original layout exactly, including the previous visibility of the Watch Pane and File Tree.
-   [ ] The Status Bar persists in all states, shows a restoration tip, and continues to update RHS coordinates.
-   [ ] The 'M' key cycle works reliably even if the user manually toggles sidebars while in Stage 1 or 2.

## 5. Out of Scope
-   Animating the layout transitions.
-   Reassigning the Escape key for layout restoration.
