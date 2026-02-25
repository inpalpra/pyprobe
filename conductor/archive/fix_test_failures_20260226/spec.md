# Specification: Fix Test Failures & Collection Errors

## 1. Overview
Update test calls to `ScalarWatchSidebar.add_scalar()` to match its new signature and resolve an IPC collection error caused by a missing `wire_protocol` module.

## 2. Functional Requirements
### 2.1 Scalar Watch Tests Update
-   **Trace ID Injection:** Update all `add_scalar(anchor, color)` calls in `tests/gui/test_scalar_watch_gui.py` and `tests/gui/test_folder_browsing.py` to `add_scalar(anchor, color, trace_id)`.
-   **ID Consistency:** Use unique `tr<n>` strings for each distinct probed symbol in the tests.
-   **Workspace Scan:** Perform a global search for `add_scalar` to ensure no production code or other tests are using the old signature.

### 2.2 IPC Collection Fix
-   **Module Restoration/Redirection:** Resolve the `ImportError: cannot import name 'wire_protocol' from 'pyprobe.ipc'`.
-   **Investigation:** Determine if `wire_protocol.py` should exist, was renamed, or if the import should point elsewhere (e.g., `pyprobe.ipc.protocol`).

## 3. Acceptance Criteria
-   `pytest` successfully collects all tests.
-   The 14 specific test failures related to `add_scalar` are resolved.
-   All tests in `tests/gui/test_scalar_watch_gui.py` and `tests/gui/test_folder_browsing.py` pass.
-   `tests/gui/test_script_runner_subprocess.py` passes.

## 4. Technical Constraints
-   Must adhere to existing coding style (PEP8, type hinting).
-   `trace_id` must follow the `tr[0-9]+` pattern.
