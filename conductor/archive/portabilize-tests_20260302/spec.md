# Specification: Portabilizing the Test Suite (Issue #10)

## Overview
The goal is to transform the `pyprobe` test suite into a "portable" package that assumes the `pyprobe` package is already installed in the environment. This will eliminate dependencies on the source code repository's layout, specifically the `pyprobe/`, `examples/`, and `regression/` directories, ensuring tests can run in isolated environments (like a clean container with only the wheel installed).

## Functional Requirements
- **Strict Portable Imports:** All tests must use `import pyprobe`. Manual `sys.path` manipulations or environment detection logic (checking for repo root) must be removed.
- **Asset Decoupling:** Move minimal required scripts and data files from `examples/` and `regression/` into `tests/data/`.
- **Path Resolution:** Update all tests to resolve paths relative to the test file itself (e.g., using `Path(__file__).parent / "data"`) instead of the repository root.
- **Dynamic Asset Generation:** For simple test scripts, consider generating them dynamically within the test's `tmp_path`.
- **CI/CD Enforcement:** Ensure that `make verify-docker` and `tests-only.yml` workflows validate portability by running tests in an isolated environment where the source code is not directly accessible.

## Non-Functional Requirements
- **Test Integrity:** The behavior and coverage of the existing tests must remain unchanged.
- **Performance:** Asset migration should not significantly increase test execution time.

## Acceptance Criteria
1. All tests in `tests/` pass in a clean environment with `pyprobe` installed as a package.
2. No tests reference `examples/` or `regression/` directories.
3. `make verify-docker` passes without the `pyprobe/` source directory being present in the test environment's `PYTHONPATH`.
4. `tests-only.yml` workflow successfully validates the installed artifact.

## Out of Scope
- Migrating *all* regression and example scripts (only the minimum required for tests).
- Modifying the core `pyprobe` application logic (refactor only).
- Adding new functional tests (unless required for asset verification).
