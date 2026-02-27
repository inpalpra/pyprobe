# Implementation Plan: Fix Symbol Highlighting in Ocean Theme

## Phase 1: Investigation and Automated Test Setup
- [x] Task: Isolate the root cause of the highlight misplacement in the Ocean theme (e.g., coordinate calculation, CSS, or PyQt style application).
- [x] Task: Write a failing unit or integration test that reproduces the offset highlight bounding box in the Ocean theme.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Investigation and Automated Test Setup' (Protocol in workflow.md) [checkpoint: b9d6026]

## Phase 2: Implementation of the Fix
- [x] Task: Implement the necessary fix to the coordinate calculations, layout engine, or style logic to correctly align the highlight rectangle.
- [x] Task: Verify that the failing test written in Phase 1 now passes (Green Phase).
- [x] Task: Conductor - User Manual Verification 'Phase 2: Implementation of the Fix' (Protocol in workflow.md) [checkpoint: d425515]

## Phase 3: Regression Testing and Multi-Theme Verification
- [ ] Task: Write or update tests to verify that the fix does not regress the "Cyberpunk" theme.
- [ ] Task: Ensure the fix applies gracefully to all affected themes, or document if it's strictly an Ocean theme issue.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Regression Testing and Multi-Theme Verification' (Protocol in workflow.md)