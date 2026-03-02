# Implementation Plan: Refactor: Separate Product Tests from Infrastructure Tests

## Phase 1: Audit and Preparation
- [ ] Task: Perform deep audit of `tests/` to identify all repository-dependent files and manual utilities.
- [ ] Task: Create `dev-tests/infra` and `dev-tests/manual` directory structure.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Audit and Preparation' (Protocol in workflow.md)

## Phase 2: Reorganization (Move Files)
- [ ] Task: Move `test_ci_config.py` and other infrastructure tests to `dev-tests/infra/`.
- [ ] Task: Move `check_scroll_click.py` and other manual scripts to `dev-tests/manual/`.
- [ ] Task: Update any internal imports or paths affected by the move.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Reorganization (Move Files)' (Protocol in workflow.md)

## Phase 3: Infrastructure Refactor
- [ ] Task: Refactor `.github/workflows/ci.yml` to add "Infra Check" job (running `dev-tests/`) and implement isolation check (deleting repo files before `tests/`).
- [ ] Task: Refactor `.github/workflows/release.yml` to enforce test isolation (ensuring product tests run without repo context).
- [ ] Task: Update `run_tests.py` to discover and execute both `tests/` and `dev-tests/` by default.
- [ ] Task: Update `scripts/test_artifact.sh` to strictly target the `tests/` directory.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Infrastructure Refactor' (Protocol in workflow.md)

## Phase 4: Final Verification
- [ ] Task: Verify local `run_tests.py` correctly executes both test suites.
- [ ] Task: Verify the full CI pipeline (including the new "Infra Check" and isolation steps) passes.
- [ ] Task: Manually verify that `tests/` can run successfully in a clean environment with only the `pyprobe` package installed.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Final Verification' (Protocol in workflow.md)
