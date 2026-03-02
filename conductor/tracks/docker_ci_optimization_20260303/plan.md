# Implementation Plan: Docker/CI Bandwidth & Speed Optimization (All-in-Base)

## Phase 1: Research & Repository Cleanup
- [ ] Task: Remove unused `Dockerfile.test`
    - [ ] Locate and delete `Dockerfile.test` at the root.
    - [ ] Verify no references exist in the codebase (Makefiles, scripts, GitHub Workflows).
- [ ] Task: Analyze existing Docker dependency flows
    - [ ] Audit `docker/ci.Dockerfile` for current installation logic.
    - [ ] Audit `docker/Dockerfile` for current installation logic.
    - [ ] Audit `scripts/test_artifact.sh` for runtime `pip install` calls.

## Phase 2: Optimize Base Image (`docker/ci.Dockerfile`)
- [ ] Task: Implement `uv` dependency baking in `docker/ci.Dockerfile`
    - [ ] Install `uv` in the base image if not already present.
    - [ ] Copy `pyproject.toml` and `uv.lock` into the base image.
    - [ ] Execute `uv sync --frozen --no-install-project --all-groups` to pre-install **all** dependencies.
    - [ ] Ensure the virtual environment is correctly located and accessible for downstream images.
- [ ] Task: Update CI build process (if applicable)
    - [ ] Verify that the base image build command (in Makefile or CI) includes the necessary files (`pyproject.toml`, `uv.lock`).

## Phase 3: Optimize Project Dockerfile & Scripts
- [ ] Task: Streamline `docker/Dockerfile`
    - [ ] Reference the updated base image.
    - [ ] Remove `pip install` or `uv sync` blocks that are now redundant.
    - [ ] Update to only copy source and install the project itself (`uv sync --frozen`).
- [ ] Task: Refactor `scripts/test_artifact.sh`
    - [ ] Remove all blocks that perform `pip install` of test dependencies (pytest-qt, scipy, etc.) at runtime inside the container.
    - [ ] Verify the script uses the pre-installed environment correctly.

## Phase 4: Verification & Checkpointing
- [ ] Task: Local Verification with `make verify-docker`
    - [ ] Run `make verify-docker` and monitor the build logs.
    - [ ] Confirm that dependency layers are either baked into the base or shown as "CACHED".
    - [ ] Verify that no network requests are made for heavy libraries during the `docker build`.
- [ ] Task: Conductor - User Manual Verification 'Docker/CI Optimization' (Protocol in workflow.md)
