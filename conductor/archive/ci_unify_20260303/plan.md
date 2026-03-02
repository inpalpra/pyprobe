# Implementation Plan - CI Unification

## Phase 1: Canonical Test Runner & Artifact Scripts
This phase establishes the foundational scripts that will be used by both developers and CI.

- [x] Task: Create `scripts/run_tests.sh` (Canonical Test Runner) c6751cd
    - [x] Implement `pytest` call with standard flags (`-v`, `--tb=short`).
    - [x] Add `--ignore` flags for known problematic tests (GUI subprocess, socket channel).
    - [x] Implement SIGSEGV (139) exit code handling for Qt cleanup.
    - [x] Make script executable.
- [x] Task: Create `scripts/test_artifact.sh` (Artifact Installer Wrapper) c6751cd
    - [x] Implement virtual environment creation in `/tmp/test-env`.
    - [x] Implement conditional installation (local wheel vs. PyPI).
    - [x] Implement source-shadowing prevention (`rm -rf pyprobe ...`).
    - [x] Implement import verification (`pyprobe.__file__`).
    - [x] Chain to `scripts/run_tests.sh`.
    - [x] Make script executable.
- [x] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

## Phase 2: Local Docker & Makefile Integration
This phase provides the isolated environment for local developers to match CI behavior.

- [x] Task: Create `docker/Dockerfile` 887de07
    - [x] Base on `python:3.12-slim`.
    - [x] Install GUI dependencies (`xvfb`, `libgl1`, `libxcb-*`, etc.).
    - [x] Copy source and build wheel inside container.
    - [x] Set default command to `scripts/test_artifact.sh wheel`.
- [x] Task: Update `Makefile` 887de07
    - [x] Add `verify-docker` target.
    - [x] Implement docker build and run logic.
- [x] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

## Phase 3: GitHub Workflow Migration
This phase replaces the old CI system with the new unified architecture.

- [x] Task: Create `.github/workflows/ci.yml` c029c84
    - [x] Implement `test-wheel` job.
    - [x] Install system dependencies (Qt/Xvfb).
    - [x] Build wheel using `uv build`.
    - [x] Execute `bash scripts/test_artifact.sh wheel`.
- [x] Task: Create `.github/workflows/release.yml` c029c84
    - [x] Implement `test-wheel` job (same as `ci.yml`).
    - [x] Implement `publish` job (using `pypa/gh-action-pypi-publish`).
    - [x] Implement `verify-pypi` job (waits for index, then `bash scripts/test_artifact.sh pypi`).
- [x] Task: Remove Legacy Workflows c029c84
    - [x] Delete legacy test workflows.
- [x] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)
