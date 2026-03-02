# Implementation Plan: Decouple Test Suite from Repository Layout

This plan outlines the steps to decouple the PyProbe test suite from the source repository's filesystem layout, as specified in `spec.md`.

## Phase 1: Research & Audit [x] [checkpoint: cdc54b9]
Goal: Identify all tests and code paths that depend on the repository root or the `regression/` directory.

- [x] Task: Audit Test Suite for Root Dependencies 2302302
    - [ ] Search for all occurrences of `os.getcwd()` in `tests/`.
    - [ ] Search for all references to the `regression/` directory in `tests/`.
    - [ ] Document all affected test files and the specific files they depend on.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Research & Audit' (Protocol in workflow.md)

## Phase 2: Relocation & Refactoring [x] [checkpoint: db16f08]
Goal: Move test helpers to a stable location and update tests to use relative path resolution.

- [x] Task: Create `tests/data/` Directory 4333baf
    - [ ] Create the directory structure.
    - [ ] Add a `.gitkeep` or initial helper script.
- [x] Task: Relocate Helper Scripts 550216a
    - [ ] Move `regression/loop.py` and other identified helpers to `tests/data/`.
    - [ ] Ensure any shared resources used by these scripts are also moved or correctly referenced.
- [x] Task: Update Path Resolution in Tests a4c7155
    - [ ] Refactor `test_cli_automation.py` to use `Path(__file__).parent / "data" / "loop.py"`.
    - [ ] Update all other audited tests to use similar robust path resolution.
    - [ ] Remove all `os.getcwd()` calls used for finding test assets.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Relocation & Refactoring' (Protocol in workflow.md)

## Phase 3: Verification & Tooling [x] [checkpoint: b00a54f]
Goal: Ensure the test suite passes in an isolated environment and provide a verification mechanism.

- [x] Task: Update Docker Verification Tooling
    - [x] Update `docker/test.Dockerfile` to remove dependency on `regression/` directory.
    - [x] Verify that `make verify-docker` passes without `regression/` copied into the container.
- [x] Task: Final Test Run via Docker
    - [x] Run `make verify-docker` and ensure all tests pass in the fully isolated container.
    - [x] Remove the temporary `scripts/verify_isolated_tests.sh`.

- [x] Task: Update CI Workflow (Optional/Advised)
    - [x] If applicable, update GitHub Actions to include an isolated test step to prevent future regressions.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Verification & Tooling' (Protocol in workflow.md)
