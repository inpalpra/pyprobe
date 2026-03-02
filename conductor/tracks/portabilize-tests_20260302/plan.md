# Implementation Plan: Portabilizing the Test Suite (Issue #10)

## Phase 1: Research & Setup [checkpoint: 0580db2]
- [x] Task: Identify all tests that depend on `examples/`, `regression/`, or repo-root path detection. 30cf21e
- [x] Task: List minimum required assets to migrate from `examples/` and `regression/` to `tests/data/`. 30cf21e
- [x] Task: Conductor - User Manual Verification 'Phase 1: Research & Setup' (Protocol in workflow.md) 0580db2

## Phase 2: Asset Migration
- [ ] Task: Create `tests/data/` if it doesn't exist and migrate identified minimum assets.
- [ ] Task: Update `tests/conftest.py` or create a new fixture to provide a stable base path for test data.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Asset Migration' (Protocol in workflow.md)

## Phase 3: Test Refactoring (TDD)
- [ ] Task: Refactor `tests/test_e2e_folder_browsing_fast.py` to use `tests/data/` and strictly portable imports.
- [ ] Task: Refactor `tests/gui/test_report_bug_dialog.py` to use `tests/data/` and strictly portable imports.
- [ ] Task: Identify and refactor all other tests using repo-root detection or `sys.path` hacks.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Test Refactoring' (Protocol in workflow.md)

## Phase 4: CI/CD & Validation
- [ ] Task: Update `make verify-docker` to ensure tests run in an isolated environment with only the installed package.
- [ ] Task: Update `.github/workflows/tests-only.yml` (if needed) to enforce portable test execution.
- [ ] Task: Verify all tests pass in a clean environment where only `tests/` and the installed package exist.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: CI/CD & Validation' (Protocol in workflow.md)
