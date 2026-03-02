# Implementation Plan: Versioned CI Image with GHCR

This track implements a versioned CI image strategy using GitHub Container Registry (GHCR) to ensure consistency and speed up CI/CD workflows.

## Phase 1: Infrastructure & Versioning [ ]

- [x] Task: Create centralized versioning file `.ci-version` 333d62d
    - [x] Create `.ci-version` containing `v1`
- [x] Task: Implement Base CI Dockerfile `docker/ci.Dockerfile` cb5967c
    - [x] Define `docker/ci.Dockerfile` with all required system and Python dependencies (Xvfb, Qt6 libs, build tools, pytest, etc.)
- [ ] Task: Create GitHub Workflow to build and push the CI image
    - [ ] Implement `.github/workflows/build-ci-image.yml`
    - [ ] Set up triggers for `docker/ci.Dockerfile` and `.ci-version`
    - [ ] Use `GITHUB_TOKEN` for GHCR authentication and push to `ghcr.io/inpalpra/pyprobe-ci:<version>`
- [ ] Task: Conductor - User Manual Verification 'Infrastructure & Versioning' (Protocol in workflow.md)

## Phase 2: Workflow Migration [ ]

- [ ] Task: Update CI workflow to use versioned GHCR image
    - [ ] Modify `.github/workflows/ci.yml` to pull image from GHCR using `.ci-version`
- [ ] Task: Update Release workflow to use versioned GHCR image
    - [ ] Modify `.github/workflows/release.yml` to pull image from GHCR using `.ci-version`
- [ ] Task: Verify CI integration
    - [ ] Confirm that a test PR triggers the CI and correctly pulls the image
- [ ] Task: Conductor - User Manual Verification 'Workflow Migration' (Protocol in workflow.md)

## Phase 3: Local Dev Parity & Cleanup [ ]

- [ ] Task: Update local Dockerfile to extend the CI base image
    - [ ] Modify `docker/Dockerfile` to use `ghcr.io/inpalpra/pyprobe-ci:<version>` as its base
- [ ] Task: Update Makefile for dynamic image tagging
    - [ ] Modify `Makefile` to read version from `.ci-version` and pass it as a build argument
- [ ] Task: Verify local Docker execution
    - [ ] Run `make verify-docker` and ensure it passes
- [ ] Task: Conductor - User Manual Verification 'Local Dev Parity & Cleanup' (Protocol in workflow.md)
