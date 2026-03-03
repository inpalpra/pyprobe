# Specification: Docker/CI Bandwidth & Speed Optimization (All-in-Base)

## Overview
Optimize Docker/CI workflows by baking **all** project dependencies into a stable base image. This ensures that the primary development and testing containers start instantly without redundant installations.

## Functional Requirements

### 1. Base Image Optimization (`docker/ci.Dockerfile`)
- **Full Dependency Baking:** Use `uv` to install **all** production and development dependencies (PyQt6, SciPy, pytest-qt, etc.) directly into the `ghcr.io/inpalpra/pyprobe-ci` base image.
- **Lockfile Synchronization:** The build process must use `uv.lock` to ensure exact version parity between the base image and the local development environment.
- **Environment Preparation:** Ensure the `uv` virtual environment (or system-wide installation) is correctly configured for downstream use.

### 2. Dockerfile Optimization (`docker/Dockerfile`)
- **Base Image Usage:** Reference the updated `ghcr.io/inpalpra/pyprobe-ci` (with all dependencies baked in).
- **Zero-Install Build:** The `docker/Dockerfile` should focus exclusively on copying the project source and installing the `pyprobe` package itself.
- **Minimal Sync:** A final `uv sync --frozen` can be run to ensure the local project is properly linked, but it should not result in any network downloads if the base image is up-to-date.

### 3. Artifact Script Refactoring (`scripts/test_artifact.sh`)
- **Eliminate All Runtime Installs:** Completely remove all `pip install` or `uv sync` calls from the artifact testing script that would require network access.
- **Environment Integrity:** Ensure the script relies entirely on the pre-installed environment within the container.

### 4. Cleanup
- **Remove `Dockerfile.test`:** Delete the unused and unreferenced `Dockerfile.test` from the repository root.

## Non-Functional Requirements
- **Performance:** Significant reduction in `make verify-docker` execution time for all builds.
- **Efficiency:** Drastic reduction in network bandwidth consumption during CI and local Docker verification.
- **Reliability:** Maintain 100% parity with existing test behavior and coverage.

## Acceptance Criteria
- `Dockerfile.test` is deleted.
- `make verify-docker` completes successfully without performing any network downloads for dependencies (PyQt6, SciPy, etc.).
- GitHub Actions CI jobs pass without regressions.
- `scripts/test_artifact.sh` executes using only the pre-baked environment.

## Out of Scope
- Optimization of non-Docker CI runners (native macOS/Windows).
- Major refactoring of the application source code.
