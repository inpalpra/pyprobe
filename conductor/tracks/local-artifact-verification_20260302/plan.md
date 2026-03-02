# Implementation Plan: Local Artifact Verification Pipeline

This plan outlines the steps to implement a high-integrity, multi-stage Docker pipeline for local artifact verification, ensuring that the `pyprobe` wheel is correctly built and fully functional in an isolated environment.

## Phase 1: Build Stage and Initial Orchestration [checkpoint: 6afbb1d]
- [x] **Task: Create Build Dockerfile**
    - [x] Create `docker/build.Dockerfile` using `python:3.12-slim`.
    - [x] Implement layer caching by copying `pyproject.toml` and `uv.lock` first.
    - [x] Configure the build stage to use `python -m build --wheel`.
- [x] **Task: Create Verification Script (Build Logic)**
    - [x] Create `scripts/verify-artifact.sh` with `set -euo pipefail`.
    - [x] Implement logic to build the Stage A image.
    - [x] Implement logic to create a temporary container and extract the built wheel to a local `dist/` directory.
    - [x] Add clear logging headers for each step.
- [x] **Task: Verify Build Isolation**
    - [x] Run `scripts/verify-artifact.sh` (build-only mode).
    - [x] Confirm that a `.whl` file is produced in the local `dist/` directory.
    - [x] Inspect the built wheel to ensure it contains expected package metadata.
- [x] **Task: Conductor - User Manual Verification 'Phase 1: Build Stage and Initial Orchestration' (Protocol in workflow.md)** 6afbb1d

## Phase 2: Isolated Test Stage with GUI Support
- [x] **Task: Create Test Dockerfile**
    - [x] Create `docker/test.Dockerfile` starting from `python:3.12-slim`.
    - [x] Install system dependencies for GUI testing: `xvfb`, `libgl1`, `libegl1`, `libdbus-1-3`, `libxkbcommon-x11-0`.
    - [x] Create a non-root user `appuser`.
    - [x] Configure `WORKDIR /workspace` and copy the built wheel, `tests/`, `regression/`, and `examples/`.
    - [x] Implement logic to create a virtual environment, install the wheel, and explicitly verify the absence of the `pyprobe/` source directory.
- [x] **Task: Update Verification Script (Test Logic)**
    - [x] Add logic to `scripts/verify-artifact.sh` to build the Stage B image.
    - [x] Add logic to run the test container under `Xvfb`.
    - [x] Ensure the script exits with a non-zero status if the tests fail.
- [x] **Task: Verify Isolated Execution**
    - [x] Run the full verification pipeline via `scripts/verify-artifact.sh`.
    - [x] Confirm that tests pass in the isolated container.
    - [x] Intentionally introduce a packaging error and confirm the pipeline fails.
- [~] **Task: Conductor - User Manual Verification 'Phase 2: Isolated Test Stage with GUI Support' (Protocol in workflow.md)**

## Phase 3: Final Orchestration and Cleanup
- [ ] **Task: Replace Makefile.docker**
    - [ ] Remove the existing `Makefile.docker`.
    - [ ] Create a new `Makefile` in the root directory.
    - [ ] Implement targets: `verify-docker`, `build-artifact`, `test-artifact`, and `clean`.
    - [ ] Ensure the `clean` target safely removes `dist/`, `build/`, and any temporary Docker artifacts.
- [ ] **Task: Final End-to-End Validation**
    - [ ] Run `make verify-docker` and confirm the entire pipeline completes successfully.
    - [ ] Verify that all intermediate containers are cleaned up.
    - [ ] Test the `make clean` target.
- [ ] **Task: Conductor - User Manual Verification 'Phase 3: Final Orchestration and Cleanup' (Protocol in workflow.md)**
