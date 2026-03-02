# Specification - CI Unification (Artifact-First & Docker-Isolated)

## 1. Overview
This track implements a unified, artifact-first CI architecture for PyProbe. The goal is to eliminate workflow drift and ensure that all tests run against built wheels rather than the source tree. This includes introducing Docker-based local isolation and a canonical test runner.

## 2. Functional Requirements
- **Canonical Test Runner:** A single entry point (`scripts/run_tests.sh`) that defines the `pytest` configuration and handles known SIGSEGV artifacts from Qt cleanup.
- **Artifact Installer Wrapper:** A script (`scripts/test_artifact.sh`) that creates a clean virtual environment, installs the PyProbe wheel (either locally built or from PyPI), and executes the canonical test runner.
- **Source-Shadowing Prevention:** The artifact installer must remove the source tree (`pyprobe/`, `pyprobe_tracer/`, etc.) within its temporary environment to ensure `import pyprobe` resolves to the installed wheel.
- **Docker Isolation:** A `Dockerfile` and `Makefile` target (`verify-docker`) to provide a consistent, head-less environment for local verification.
- **Unified GitHub Workflows:**
    - `ci.yml`: Triggered on PRs/pushes to `main`. Builds the wheel and tests it.
    - `release.yml`: Triggered on tags. Builds, tests, publishes to PyPI, and performs a post-publish verification test from PyPI.

## 3. Non-Functional Requirements
- **Zero-Duplication:** Test runner configuration (ignored tests, flags) should only be defined in one place.
- **Platform-Agnosticism:** Scripts should work on Linux (CI) and macOS (local dev).
- **Graceful Failures:** SIGSEGV during Qt cleanup should be treated as success if the test suite passed.

## 4. Acceptance Criteria
- `scripts/run_tests.sh` correctly executes the test suite.
- `scripts/test_artifact.sh wheel` successfully installs a local wheel and passes tests.
- `scripts/test_artifact.sh pypi` successfully installs from PyPI and passes tests.
- `make verify-docker` runs the full build-and-test cycle inside a container.
- GitHub `ci.yml` replaces existing workflows and passes on PRs.
- GitHub `release.yml` replaces existing release workflows and successfully verifies the PyPI artifact.

## 5. Out of Scope
- Migrating non-test tasks (linting, type checking) to this specific unified architecture (unless they are part of the current pytest suite).
- Supporting non-Debian based Linux distributions for the Docker container.
- Windows-specific CI runners.
