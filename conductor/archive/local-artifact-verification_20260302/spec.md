# Specification: Local Artifact Verification Pipeline (Track: local-artifact-verification_20260302)

## Overview
This track implements a high-integrity, multi-stage artifact verification pipeline for `pyprobe`. The goal is to provide a local mechanism to build and validate the distribution wheel in complete isolation, mimicking and strengthening the project's CI verification process. This ensures that the published artifact is functionally complete, correctly packaged, and free from source-tree dependencies.

## Functional Requirements
1.  **Two-Stage Docker Workflow:**
    *   **Stage A (Build):** A dedicated container (`docker/build.Dockerfile`) to build the `pyprobe` wheel from source using `python -m build`. It must only export the `.whl` artifact.
    *   **Stage B (Test):** A separate, fresh container (`docker/test.Dockerfile`) that installs the built wheel into a clean virtual environment and runs the full test suite.
2.  **Isolation Guarantees:**
    *   The test container must NOT have access to the `pyprobe/` source directory during test execution.
    *   The test container must run as a non-root user (`appuser`).
    *   No shared filesystem state between build and test stages.
3.  **Full Test Suite Support:**
    *   The test container must include `Xvfb` (X virtual framebuffer) to support GUI tests.
    *   All tests (`pytest`) must pass within the isolated environment.
4.  **Orchestration:**
    *   A shell script (`scripts/verify-artifact.sh`) to automate the end-to-end process: build, extract, and test.
    *   A centralized `Makefile` (replacing the current `Makefile.docker`) to provide easy-to-use targets for the pipeline.

## Non-Functional Requirements
- **Determinism:** The pipeline must yield identical results across different local environments (macOS, Linux).
- **Security:** Use non-root users in the test stage and avoid world-writable directories.
- **Performance:** Optimize Docker layer caching by copying dependency manifests (e.g., `pyproject.toml`, `uv.lock`) before the full source tree.

## Acceptance Criteria
- [ ] `Makefile.docker` is successfully removed and replaced by a new `Makefile`.
- [ ] `scripts/verify-artifact.sh` successfully builds a wheel in a build container.
- [ ] `scripts/verify-artifact.sh` successfully extracts the wheel and runs full tests (including GUI tests via Xvfb) in a test container.
- [ ] Tests in the test container fail if the wheel is missing dependencies or incorrectly packaged.
- [ ] The test container environment contains no `pyprobe/` source directory at execution time (only the installed package in site-packages).

## Out of Scope
- Integration with external PyPI repositories (this is for local verification).
- Building source distributions (`sdist`), focusing exclusively on wheels (`.whl`).
