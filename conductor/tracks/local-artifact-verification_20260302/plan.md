# Implementation Plan: Local Artifact Verification Pipeline

This plan outlines the steps to implement a high-integrity, multi-stage Docker pipeline for local artifact verification, ensuring that the `pyprobe` wheel is correctly built and fully functional in an isolated environment.

## Phase 1: Build Stage and Initial Orchestration
- [ ] **Task: Create Build Dockerfile**
    - [ ] Create `docker/build.Dockerfile` using `python:3.12-slim`.
    - [ ] Implement layer caching by copying `pyproject.toml` and `uv.lock` first.
    - [ ] Configure the build stage to use `python -m build --wheel`.
- [ ] **Task: Create Verification Script (Build Logic)**
    - [ ] Create `scripts/verify-artifact.sh` with `set -euo pipefail`.
    - [ ] Implement logic to build the Stage A image.
    - [ ] Implement logic to create a temporary container and extract the built wheel to a local `dist/` directory.
    - [ ] Add clear logging headers for each step.
- [ ] **Task: Verify Build Isolation**
    - [ ] Run `scripts/verify-artifact.sh` (build-only mode).
    - [ ] Confirm that a `.whl` file is produced in the local `dist/` directory.
    - [ ] Inspect the built wheel to ensure it contains expected package metadata.
- [ ] **Task: Conductor - User Manual Verification 'Phase 1: Build Stage and Initial Orchestration' (Protocol in workflow.md)**

## Phase 2: Isolated Test Stage with GUI Support
- [ ] **Task: Create Test Dockerfile**
    - [ ] Create `docker/test.Dockerfile` starting from `python:3.12-slim`.
    - [ ] Install system dependencies for GUI testing: `xvfb`, `libgl1-mesa-glx`, `libegl1`, `libdbus-1-3`, `libxkbcommon-x11-0`.
    - [ ] Create a non-root user `appuser`.
    - [ ] Configure `WORKDIR /workspace` and copy the built wheel, `tests/`, `regression/`, and `examples/`.
    - [ ] Implement logic to create a virtual environment, install the wheel, and explicitly verify the absence of the `pyprobe/` source directory.
- [ ] **Task: Update Verification Script (Test Logic)**
    - [ ] Add logic to `scripts/verify-artifact.sh` to build the Stage B image.
    - [ ] Add logic to run the test container under `Xvfb`.
    - [ ] Ensure the script exits with a non-zero status if the tests fail.
- [ ] **Task: Verify Isolated Execution**
    - [ ] Run the full verification pipeline via `scripts/verify-artifact.sh`.
    - [ ] Confirm that tests pass in the isolated container.
    - [ ] Intentionally introduce a packaging error (e.g., exclude a required file in `pyproject.toml`) and confirm the pipeline fails.
- [ ] **Task: Conductor - User Manual Verification 'Phase 2: Isolated Test Stage with GUI Support' (Protocol in workflow.md)**

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
