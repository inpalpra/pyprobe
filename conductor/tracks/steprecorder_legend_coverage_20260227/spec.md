# Track: Missing StepRecorder coverage for legend trace toggles

## Overview
Currently, toggling trace visibility via plot legend clicks in PyProbe Plots is not recorded by the `StepRecorder`. This creates a gap in the structured bug report's "Steps to Reproduce" section, as user-driven visibility changes are essential UI state transitions.

## Problem
When a user clicks a legend entry to toggle a trace's visibility:
- The visibility changes visually on the plot.
- No `StepRecorder` entry is created.
- This affects windows with multiple overlays or format lenses that produce multiple traces (e.g., "Mag & Phase").

## Goals
1. **Record user-driven legend clicks:** When a user clicks a legend entry, the `StepRecorder` should record a step like:
   `Toggled visibility of <trace_name> in window <wN> (<anchor.identity_label()>)`
2. **Strict TDD:** Implement failing tests first, then the fix.
3. **No Regressions:** Ensure no accidental recording during initialization, lens switches, or redraws.

## Functional Requirements
- Introduce a new domain-level Qt signal `legend_trace_toggled(str, bool)` (trace_name, is_visible) if no suitable signal exists.
- The signal must emit exactly once per user click, AFTER the state changes.
- In `MainWindow._show_report_bug_dialog()`, wire this signal to the `StepRecorder`'s `signal_sources`.
- Derive the internal window ID (e.g., `w0`) and the anchor's identity label for the message.

## Non-Functional Requirements
- **Performance:** Ensure no impact on rendering performance.
- **Stability:** Defensive handling (e.g., `getattr`) if a panel is partially destroyed.
- **Maintainability:** Do NOT modify `StepRecorder` core logic or `BugReport` data model.

## Acceptance Criteria
- [ ] Toggling trace visibility via legend click records a step in the bug report.
- [ ] No step is recorded when `StepRecorder` is inactive.
- [ ] No step is recorded during automated visibility changes (e.g., lens switching).
- [ ] The recorded message matches the format: `Toggled visibility of Phase in window w0 (received_symbols @ dsp_demo.py:72:8)`.
- [ ] All existing regression tests pass.

## Out of Scope
- Recording hover events.
- Recording internal `setVisible()` calls not triggered by user legend interaction.
