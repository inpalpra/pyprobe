# Implementation Plan: Fix Test Failures & Collection Errors

## Phase 1: IPC Collection Fix
- [x] Task: Research `wire_protocol` in `pyprobe/ipc/socket_channel.py` [28b4d55]
- [x] Task: Fix `ImportError` in `socket_channel.py` (Implement stub or correct path) [28b4d55]
- [x] Task: Verify `uv run pytest --collect-only` succeeds [28b4d55]
- [ ] Task: Conductor - User Manual Verification 'Phase 1: IPC Collection Fix' (Protocol in workflow.md)

## Phase 2: Scalar Watch Tests Update
- [ ] Task: Update `add_scalar` calls in `tests/gui/test_scalar_watch_gui.py`.
    - [ ] Inject `trace_id` (tr0, tr1, etc.) into all calls.
    - [ ] Verify tests pass: `uv run pytest tests/gui/test_scalar_watch_gui.py`.
- [ ] Task: Update `add_scalar` calls in `tests/gui/test_folder_browsing.py`.
    - [ ] Inject `trace_id` into all calls.
    - [ ] Verify tests pass: `uv run pytest tests/gui/test_folder_browsing.py`.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Scalar Watch Tests Update' (Protocol in workflow.md)

## Phase 3: Global Audit & Final Validation
- [ ] Task: Global `grep` for outdated `add_scalar(..., ...)` calls (2 args).
- [ ] Task: Run full test suite: `uv run pytest --cov=pyprobe`.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Global Audit & Final Validation' (Protocol in workflow.md)
