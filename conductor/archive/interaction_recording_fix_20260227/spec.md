# Specification: Comprehensive Interaction Recording Fix

## Overview
The "Step Recording" system in PyProbe is intended to capture all significant user interactions to enable "forensic-grade" reproducibility in bug reports. Currently, several key interactions are not being recorded or are recorded incorrectly, leading to incomplete "Steps to Reproduce" lists.

## Functional Requirements
1.  **Lens/Format Changes:**
    -   Record when a user changes the visualization lens (e.g., Mag, Phase, Constellation) via the plot dropdown menu.
    -   Output format: `Changed format on window w<n> to <Format Name>`.
2.  **Legend Interaction (Trace Visibility):**
    -   Record when a user toggles the visibility of a trace.
    -   **Constraint:** This recording should occur **ONLY WHEN THERE ARE MULTIPLE OVERLAID TRACES IN A WINDOW**.
    -   **Precision:** The recording is triggered specifically when the user **CLICKS ON THE LITTLE HORIZONTAL LINE REPRESENTING THE TRACE LEGEND** for the signal they want to show/hide.
    -   Output format: `Toggled visibility of <Trace Name> in window w<n>`.
3.  **Equation Management:**
    -   Record when an existing equation is edited in the Equation Editor.
    -   (Note: "Add Equation" is already working).
4.  **Execution Control Clarity:**
    -   Fix a bug where "Clicked RUN" is occasionally recorded as "Clicked Pause".
    -   Ensure consistent identity for execution state transitions.

## Non-Functional Requirements
-   **Performance:** Recording must be non-blocking and have negligible impact on UI responsiveness.
-   **Reliability:** Steps must be recorded in the exact order they occur.

## Acceptance Criteria
-   [ ] Changing a lens in window `w0` to "Mag and Phase" results in the step: `Changed format on window w0 to Mag and Phase`.
-   [ ] In a window with multiple overlaid traces (e.g., `w1`), clicking the little horizontal line for `ref_signal` in the legend results in the step: `Toggled visibility of ref_signal in window w1`.
-   [ ] Editing an equation `eq0` results in a recorded step reflecting the change.
-   [ ] Clicking "Run" and "Pause" results in correctly labeled steps in the reproduction list.

## Out of Scope
-   Automated "Restoration" of these states.
-   Recording panel move/resize events (UI layout changes).
