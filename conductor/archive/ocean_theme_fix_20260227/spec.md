# Specification: Fix Symbol Highlighting in Ocean Theme

## Overview
The "Ocean" theme currently renders symbol highlights in the code view pane incorrectly. The highlight rectangles appear misplaced, offset, and spill over onto adjacent symbols and text, affecting the legibility and user experience of the debugger. This track will investigate the root cause of this misplacement and implement a fix, ensuring the Ocean theme renders highlights as accurately as the default "Cyberpunk" theme.

## Functional Requirements
- Investigate and fix the coordinate calculation or layout rendering logic related to the Ocean theme's symbol highlighting in the code view pane.
- Ensure the highlight rectangle correctly bounds the targeted symbol without spilling over to neighboring text or symbols.
- Verify if other themes are affected by the same root cause and apply the fix universally if applicable.

## Non-Functional Requirements
- The fix must not introduce regressions into the "Cyberpunk" theme (which currently functions correctly).
- The solution should maintain the existing performance of the code view rendering.

## Acceptance Criteria
- [ ] Run `./.venv/bin/python -m pyprobe examples/dsp_demo.py`.
- [ ] Switch the active theme to "Ocean".
- [ ] Probe the variables `signal_i`, `signal_q`, and `received_symbols`.
- [ ] Verify that the highlight rectangles in the code view area perfectly align with the probed symbols, with no offset or spillage.
- [ ] Switch back to the "Cyberpunk" theme and verify that symbol highlighting remains correct.

## Out of Scope
- Complete redesign of the Ocean theme or any other themes.
- Fixing unrelated rendering issues outside of the symbol highlights in the code view pane.