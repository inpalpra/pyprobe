# Specification: Decouple Test Suite from Repository Layout

## Overview
The PyProbe test suite (specifically `test_cli_automation.py`) is currently coupled to the source repository's filesystem layout, relying on files in `regression/` and using `os.getcwd()`. This causes failures in isolated environments (e.g., testing an installed wheel). This track will decouple the tests to ensure they validate the installed artifact independently of the source tree.

## Functional Requirements
- **Relocate Test Helpers:** Move necessary scripts from `regression/` (like `loop.py`) into a dedicated `tests/data/` directory.
- **Path Resolution:** Update tests to resolve these helper scripts relative to the test file (e.g., using `Path(__file__).parent`) instead of using `os.getcwd()` or hardcoded relative paths from the root.
- **Comprehensive Audit:** Identify and fix all instances across the entire test suite where tests depend on the repository's root structure or the `regression/` directory.
- **Isolated Execution:** Ensure `pytest` can run and pass when only the `tests/` directory and an installed `pyprobe` package are present.

## Non-Functional Requirements
- **Reliability:** Tests must be robust against changes in the developer's current working directory.
- **Maintainability:** Standardize the location and access pattern for test assets.

## Acceptance Criteria
- [ ] All references to the `regression/` directory are removed from the `tests/` suite.
- [ ] No test uses `os.getcwd()` to locate its own resources or helper scripts.
- [ ] All tests pass when executed from an arbitrary directory against an installed `pyprobe` wheel.
- [ ] Verification script/command exists to run tests in an isolated environment (e.g., using a fresh venv or Docker).

## Out of Scope
- Rewriting the tests themselves (only path/resource logic is changed).
- Changes to the `pyprobe` package's core logic (unless required for resource access, though "Relocation" strategy shouldn't require it).
