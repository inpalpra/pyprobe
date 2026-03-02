# Specification: Refactor: Separate Product Tests from Infrastructure Tests

## Overview
This track involves a significant reorganization of the `pyprobe` test suite to enforce a clear boundary between product-level tests (which should only depend on the installed `pyprobe` package) and development/infrastructure tests (which may depend on the full repository context).

## Functional Requirements
1.  **Deep Audit & Move:** Scan `tests/` for all scripts and tests that require the full repository context (e.g., `Makefile`, `.github/`, `scripts/`, `Dockerfile`) or are manual utilities.
2.  **Move to `dev-tests/`:**
    *   Infrastructure/Config tests (`test_ci_config.py`) move to `dev-tests/infra/`.
    *   Manual utilities (`check_scroll_click.py`) move to `dev-tests/manual/`.
    *   Any other scripts identified as repository-dependent or non-automated should be moved.
3.  **CI Workflow Update (`ci.yml`):**
    *   Add a new "Infra Check" job that runs `pytest dev-tests/` immediately.
    *   Configure this job to fail the entire pipeline if infrastructure tests fail.
    *   **Isolation Check:** In the product test job, after `dev-tests/` completion, simulate a "clean environment" by deleting repository-specific files (like `Makefile`, `.git/`, `scripts/`) before running `pytest tests/`.
4.  **Local Runner Update (`run_tests.py`):**
    *   Update discovery logic to include both `tests/` and `dev-tests/` by default.
5.  **Release Workflow (`release.yml`):** Ensure the same isolation principle applies to release testing.
    *   Refactor `release.yml` to ensure product tests are run without repo context.

## Non-Functional Requirements
-   **Test Portability:** The `tests/` directory must be runnable against an installed wheel without access to the source code repository.
-   **Zero Regressions:** Product functionality must still be fully verified by the remaining `tests/`.

## Acceptance Criteria
-   `tests/` directory is free of any repository-dependent files or manual scripts.
-   `dev-tests/` contains all identified infrastructure and manual tests.
-   The "Infra Check" job correctly fails the CI pipeline on failures.
-   The product test job in CI passes even after repo-specific files are deleted.
-   `run_tests.py` runs both `tests/` and `dev-tests/` by default.

## Out of Scope
-   Writing new feature tests or fixing unrelated bugs.
-   Large-scale refactoring of the internal test logic (unless required for separation).
