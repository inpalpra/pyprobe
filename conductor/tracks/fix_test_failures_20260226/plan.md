# Implementation Plan: Fix Test Failures & Collection Errors

## Phase 1: IPC Collection Fix [checkpoint: 9de2c7c]
- [x] Task: Research `wire_protocol` in `pyprobe/ipc/socket_channel.py` [28b4d55]
- [x] Task: Fix `ImportError` in `socket_channel.py` (Implement stub or correct path) [28b4d55]
- [x] Task: Verify `uv run pytest --collect-only` succeeds [28b4d55]
- [x] Task: Conductor - User Manual Verification 'Phase 1: IPC Collection Fix' (Protocol in workflow.md) [9de2c7c]

## Phase 2: Scalar Watch Tests Update [checkpoint: 0176ff9]
- [x] Task: Update `add_scalar` calls in `tests/gui/test_scalar_watch_gui.py` [dee819a].
    - [x] Inject `trace_id` (tr0, tr1, etc.) into all calls.
    - [x] Verify tests pass: `uv run pytest tests/gui/test_scalar_watch_gui.py`.
- [x] Task: Update `add_scalar` calls in `tests/gui/test_folder_browsing.py` [dee819a].
    - [x] Inject `trace_id` into all calls.
    - [x] Verify tests pass: `uv run pytest tests/gui/test_folder_browsing.py`.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Scalar Watch Tests Update' (Protocol in workflow.md) [0176ff9]

## Phase 3: Global Audit & Final Validation
- [x] Task: Global `grep` for outdated `add_scalar(..., ...)` calls (2 args) [dee819a].
- [x] Task: Run full test suite: `uv run pytest --cov=pyprobe` [3442d4a].
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Global Audit & Final Validation' (Protocol in workflow.md)
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Global Audit & Final Validation' (Protocol in workflow.md)
