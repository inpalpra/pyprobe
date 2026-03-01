# Specification: Resolve GitHub CI E2E GUI Test Failure (Race Condition)

## Overview
A deterministic failure occurs in the E2E GUI test suite on GitHub Actions (Ubuntu), specifically suspected to be a race condition in the `export_and_quit` workflow. The `RedrawThrottler` memory buffer contains correct Frame 1 data, but the `WaveformWidget` may still hold stale Frame 0 data because the Qt event loop has not yet processed the pending `setData` update. This discrepancy is only visible in the headless CI environment, possibly due to different event loop timing or resource constraints.

## Functional Requirements
- **Debug Infrastructure Repair:** Fix and update `.github/workflows/debug-targeted.yml` to enable isolated, rapid execution of specific failing E2E tests in the GitHub Actions environment.
- **Synchronous Widget Flushing:** Implement a mechanism to ensure that the `WaveformWidget` state is synchronously flushed and that all pending Qt events (specifically `setData` calls) are processed before an export or application quit occurs.
- **Race Condition Resolution:** Address the synchronization gap between the `RedrawThrottler` data buffer and the actual rendered widget state to ensure "What You See Is What You Export."
- **Experimental Verification:** Formulate hypotheses for additional potential failures and write temporary, targeted tests to confirm or disprove them using the fixed `debug-targeted.yml` pipeline.

## Acceptance Criteria
- `debug-targeted.yml` successfully isolates and runs single test cases on GitHub.
- E2E GUI tests pass consistently on the GitHub Ubuntu runner.
- Root cause (confirmed as the `export_and_quit` race or otherwise) is mitigated and documented.
- Synchronous state flushing is verified to work correctly in headless environments.

## Out of Scope
- Redesigning the `RedrawThrottler` beyond what is necessary for this fix.
- General CI performance tuning unrelated to this specific failure.
- Major refactoring of the `WaveformWidget` rendering pipeline.
