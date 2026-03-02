You are designing an enterprise-grade, artifact-verification pipeline for a Python project named "pyprobe".

The objective is to validate the built wheel exactly as it would behave when installed from PyPI, using a fully isolated, two-container Docker workflow plus a Makefile orchestrator.

This must simulate (and strengthen) the verify-pypi CI job locally with maximum isolation, determinism, and reproducibility.

============================================================
ARCHITECTURE OVERVIEW
============================================================

We want a TWO-STAGE verification pipeline:

Stage A — Build Container
- Builds ONLY the wheel artifact using:
      python -m build --wheel
- Produces dist/*.whl
- Does NOT run tests
- Exports the built wheel to the host

Stage B — Test Container
- Starts from a fresh Python image
- Receives ONLY the built wheel (not the source tree)
- Copies test fixtures (tests/, regression/, examples/)
- Creates a clean virtual environment
- Installs the wheel
- Ensures no source package directories exist
- Runs pytest against the installed wheel
- Runs as a non-root user

The build container and test container must NOT share filesystem state.

============================================================
FILES TO GENERATE
============================================================

1) docker/build.Dockerfile
2) docker/test.Dockerfile
3) scripts/verify_artifact.sh
4) Makefile

============================================================
GLOBAL REQUIREMENTS
============================================================

GENERAL:
- Base image: python:3.12-slim
- Use python -m build --wheel (wheel only)
- Use pytest
- Fail fast on any error
- No editable installs
- No access to source package during test stage
- Clear logging messages explaining each step
- Deterministic behavior
- No docker-compose

ISOLATION GUARANTEES:
- Test container must NOT contain pyprobe/ source directory
- Test container must NOT contain *.egg-info
- Tests must import only the installed site-packages version
- If accidental shadowing occurs, the pipeline should fail loudly

SECURITY:
- Stage B must create a non-root user (e.g., appuser)
- pytest must run under that non-root user
- No world-writable directories

PERFORMANCE:
- Optimize Docker layer caching
- In Stage A:
    * Copy pyproject.toml (and any lockfiles such as uv.lock, poetry.lock, requirements*.txt) first
    * Install build dependencies
    * Then copy the rest of the source tree
- This ensures dependency installation layers are cached when only source code changes

============================================================
DOCKER STAGE A: BUILD CONTAINER
============================================================

Responsibilities:
- WORKDIR /workspace
- Copy pyproject.toml and lockfiles first
- Install build tools
- Copy the rest of the repo
- Run python -m build --wheel
- Leave artifact in /workspace/dist/

No testing occurs here.

============================================================
DOCKER STAGE B: TEST CONTAINER
============================================================

Responsibilities:
- Start from clean python:3.12-slim
- Create non-root user (appuser)
- WORKDIR /workspace
- Copy only:
      dist/*.whl
      tests/
      regression/
      examples/
- Create virtual environment at /verify-env
- Install wheel into that venv
- Explicitly verify no source package directories exist
- Run pytest tests
- Execute pytest as non-root user

============================================================
VERIFY SCRIPT
============================================================

scripts/verify_artifact.sh must:

1) Use: set -euo pipefail
2) Print clear section headers
3) Build Stage A image
4) Create temporary container from Stage A
5) Copy dist/ out of container to local dist/
6) Remove temporary container
7) Build Stage B image
8) Run Stage B container
9) Exit non-zero if tests fail
10) Clean up intermediate containers automatically

Script must:
- Work on macOS (Apple Silicon) and Linux
- Avoid destructive wildcard rm -rf patterns
- Use find -maxdepth 1 when deleting egg-info directories
- Be safe and explicit

============================================================
MAKEFILE TARGETS
============================================================

Makefile must include:

verify-docker:
    Runs scripts/verify_artifact.sh

build-artifact:
    Only builds Stage A container and extracts dist/

test-artifact:
    Assumes dist/ exists
    Builds Stage B image
    Runs Stage B container

clean:
    Removes:
        dist/
        build/
        *.egg-info (safely)
    Optionally prunes dangling Docker images

Makefile must:
- Be POSIX compatible
- Not rely on GNU-only extensions
- Use tabs (not spaces)
- Be production-ready

============================================================
OUTPUT FORMAT
============================================================

Return:

- docker/build.Dockerfile
- docker/test.Dockerfile
- scripts/verify_artifact.sh
- Makefile