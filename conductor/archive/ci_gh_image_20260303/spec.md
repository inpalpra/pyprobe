# Specification: Versioned CI Image with GHCR

## Overview
Implement a versioned CI image strategy using GitHub Container Registry (GHCR) for the PyProbe project. This track involves creating a base CI image, setting up a workflow to build and push it, and migrating existing CI and release workflows to use this versioned image. It also ensures local development parity by updating the local `Dockerfile` to extend the CI base image.

## Functional Requirements
1.  **Centralized Versioning:** Create a `.ci-version` file at the project root to store the current CI image version (e.g., `v1`).
2.  **Base CI Image:** Implement `docker/ci.Dockerfile` with all necessary system and Python dependencies for PyProbe's CI (Xvfb, Qt6 libs, build tools, pytest, etc.).
3.  **Build Workflow:** Implement `.github/workflows/build-ci-image.yml` to automatically build and push the CI image to GHCR when `docker/ci.Dockerfile` or `.ci-version` changes.
4.  **Workflow Migration:**
    *   Update `.github/workflows/ci.yml` to use the versioned CI image from GHCR.
    *   Update `.github/workflows/release.yml` to use the versioned CI image from GHCR.
5.  **Local Dev Parity:**
    *   Update `docker/Dockerfile` to extend the versioned CI base image.
    *   Ensure `make verify-docker` works correctly using the new image.
6.  **Makefile Updates:** Update the `Makefile` to support building the local Docker image with the correct base tag from `.ci-version`.

## Non-Functional Requirements
- **Performance:** Reduce CI runtime by avoiding redundant `apt-get install` and `pip install` steps in every workflow run.
- **Reliability:** Ensure CI and Release environments are consistent and immutable for a given version.

## Acceptance Criteria
1.  `.ci-version` file exists and controls the image tag.
2.  `build-ci-image.yml` successfully pushes a versioned image to GHCR.
3.  `ci.yml` successfully runs tests using the image from GHCR.
4.  `release.yml` successfully builds and tests the wheel using the image from GHCR.
5.  `make verify-docker` runs successfully locally.

## Out of Scope
- Automatic version bumping (manual updates to `.ci-version` only).
- Multi-architecture images (x86_64 only for now).
