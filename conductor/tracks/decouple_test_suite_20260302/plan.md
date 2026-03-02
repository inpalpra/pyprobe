# Implementation Plan: Decouple Test Suite from Repository Layout

This plan outlines the steps to decouple the PyProbe test suite from the source repository's filesystem layout, as specified in `spec.md`.

## Phase 1: Research & Audit [ ]
Goal: Identify all tests and code paths that depend on the repository root or the `regression/` directory.

- [ ] Task: Audit Test Suite for Root Dependencies
    - [ ] Search for all occurrences of `os.getcwd()` in `tests/`.
    - [ ] Search for all references to the `regression/` directory in `tests/`.
    - [ ] Document all affected test files and the specific files they depend on.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Research & Audit' (Protocol in workflow.md)

## Phase 2: Relocation & Refactoring [ ]
Goal: Move test helpers to a stable location and update tests to use relative path resolution.

- [ ] Task: Create `tests/data/` Directory
    - [ ] Create the directory structure.
    - [ ] Add a `.gitkeep` or initial helper script.
- [ ] Task: Relocate Helper Scripts
    - [ ] Move `regression/loop.py` and other identified helpers to `tests/data/`.
    - [ ] Ensure any shared resources used by these scripts are also moved or correctly referenced.
- [ ] Task: Update Path Resolution in Tests
    - [ ] Refactor `test_cli_automation.py` to use `Path(__file__).parent / "data" / "loop.py"`.
    - [ ] Update all other audited tests to use similar robust path resolution.
    - [ ] Remove all `os.getcwd()` calls used for finding test assets.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Relocation & Refactoring' (Protocol in workflow.md)

## Phase 3: Verification & Tooling [ ]
Goal: Ensure the test suite passes in an isolated environment and provide a verification mechanism.

- [ ] Task: Create Isolation Verification Script
    - [ ] Create a script (e.g., `scripts/verify_isolated_tests.sh`) that builds a wheel, installs it in a temporary venv, and runs `pytest` from a different directory using only the `tests/` folder.
- [ ] Task: Final Test Run & Fixes
    - [ ] Run the full test suite in the isolated environment.
    - [ ] Fix any remaining coupling issues discovered during the final run.
- [ ] Task: Update CI Workflow (Optional/Advised)
    - [ ] If applicable, update GitHub Actions to include an isolated test step to prevent future regressions.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Verification & Tooling' (Protocol in workflow.md)
