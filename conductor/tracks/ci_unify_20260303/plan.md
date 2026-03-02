# Implementation Plan - CI Unification

## Phase 1: Canonical Test Runner & Artifact Scripts
This phase establishes the foundational scripts that will be used by both developers and CI.

- [ ] Task: Create `scripts/run_tests.sh` (Canonical Test Runner)
    - [ ] Implement `pytest` call with standard flags (`-v`, `--tb=short`).
    - [ ] Add `--ignore` flags for known problematic tests (GUI subprocess, socket channel).
    - [ ] Implement SIGSEGV (139) exit code handling for Qt cleanup.
    - [ ] Make script executable.
- [ ] Task: Create `scripts/test_artifact.sh` (Artifact Installer Wrapper)
    - [ ] Implement virtual environment creation in `/tmp/test-env`.
    - [ ] Implement conditional installation (local wheel vs. PyPI).
    - [ ] Implement source-shadowing prevention (`rm -rf pyprobe ...`).
    - [ ] Implement import verification (`pyprobe.__file__`).
    - [ ] Chain to `scripts/run_tests.sh`.
    - [ ] Make script executable.
- [ ] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

## Phase 2: Local Docker & Makefile Integration
This phase provides the isolated environment for local developers to match CI behavior.

- [ ] Task: Create `docker/Dockerfile`
    - [ ] Base on `python:3.12-slim`.
    - [ ] Install GUI dependencies (`xvfb`, `libgl1`, `libxcb-*`, etc.).
    - [ ] Copy source and build wheel inside container.
    - [ ] Set default command to `scripts/test_artifact.sh wheel`.
- [ ] Task: Update `Makefile`
    - [ ] Add `verify-docker` target.
    - [ ] Implement docker build and run logic.
- [ ] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

## Phase 3: GitHub Workflow Migration
This phase replaces the old CI system with the new unified architecture.

- [ ] Task: Create `.github/workflows/ci.yml`
    - [ ] Implement `test-wheel` job.
    - [ ] Install system dependencies (Qt/Xvfb).
    - [ ] Build wheel using `uv build`.
    - [ ] Execute `bash scripts/test_artifact.sh wheel`.
- [ ] Task: Create `.github/workflows/release.yml`
    - [ ] Implement `test-wheel` job (same as `ci.yml`).
    - [ ] Implement `publish` job (using `pypa/gh-action-pypi-publish`).
    - [ ] Implement `verify-pypi` job (waits for index, then `bash scripts/test_artifact.sh pypi`).
- [ ] Task: Remove Legacy Workflows
    - [ ] Delete legacy test workflows.
- [ ] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)
