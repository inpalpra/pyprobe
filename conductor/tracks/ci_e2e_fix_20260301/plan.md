# Implementation Plan: Resolve GitHub CI E2E GUI Test Failure (Race Condition)

## Phase 1: CI Debug Infrastructure & Diagnostic Collection
Fix the debug pipeline and collect evidence before proposing any fix.

- [ ] Task: Fix `.github/workflows/debug-targeted.yml` to support isolated E2E GUI test runs (e.g., via `inputs` for test files/patterns).
- [ ] Task: Collect and analyze existing CI logs from the failing run (Run ID `22533427606`). Look for `[DIAG-BUF]` and `[DIAG-PANEL]` stderr output — these are embedded diagnostics showing throttler buffer vs widget state. See `docs/ci_debug_report.md` for context.
- [ ] Task: Run the failing test (`test_overlay_drag_drop_two_frames_fast.py`) in isolation via `debug-targeted.yml` and capture full stderr/stdout.
- [ ] Task: Confirm or refute the current hypothesis: that the `RedrawThrottler` buffer holds correct data but the `WaveformWidget` has not consumed it by export time.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: CI Debug Infrastructure & Diagnostic Collection' (Protocol in workflow.md)

## Phase 2: Root Cause Fix
Implement a fix based on Phase 1 findings. Do NOT begin this phase until Phase 1 diagnosis is complete and the root cause is confirmed.

- [ ] Task: Based on diagnosis, identify the correct fix (candidates: synchronous widget flush, deeper `processEvents()` draining, explicit data sync bypass, or other).
- [ ] Task: Implement the fix in the minimal scope required.
- [ ] Task: Verify the fix passes locally on macOS before pushing to CI.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Root Cause Fix' (Protocol in workflow.md)

## Phase 3: Validation and Regression Testing
Verify the fix in CI and ensure no regressions.

- [ ] Task: Run the failing test on the GitHub Actions Ubuntu runner and confirm it passes.
- [ ] Task: Run the full E2E GUI test suite on CI to check for regressions.
- [ ] Task: Verify local macOS tests still pass.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Validation and Regression Testing' (Protocol in workflow.md)
