# Implementation Plan: Versioned CI Image with GHCR

This track implements a versioned CI image strategy using GitHub Container Registry (GHCR) to ensure consistency and speed up CI/CD workflows.

## Phase 1: Infrastructure & Versioning [checkpoint: 76ba093]

- [x] Task: Create centralized versioning file `.ci-version` 333d62d
    - [x] Create `.ci-version` containing `v1`
- [x] Task: Implement Base CI Dockerfile `docker/ci.Dockerfile` cb5967c
    - [x] Define `docker/ci.Dockerfile` with all required system and Python dependencies (Xvfb, Qt6 libs, build tools, pytest, etc.)
- [x] Task: Create GitHub Workflow to build and push the CI image a06a7c6
    - [x] Implement `.github/workflows/build-ci-image.yml`
    - [x] Set up triggers for `docker/ci.Dockerfile` and `.ci-version`
    - [x] Use `GITHUB_TOKEN` for GHCR authentication and push to `ghcr.io/inpalpra/pyprobe-ci:<version>`
- [x] Task: Conductor - User Manual Verification 'Infrastructure & Versioning' (Protocol in workflow.md) 76ba093

## Phase 2: Workflow Migration [checkpoint: 961f11f]

- [x] Task: Update CI workflow to use versioned GHCR image 925a2b1
    - [x] Modify `.github/workflows/ci.yml` to pull image from GHCR using `.ci-version`
- [x] Task: Update Release workflow to use versioned GHCR image 5157b17
    - [x] Modify `.github/workflows/release.yml` to pull image from GHCR using `.ci-version`
- [x] Task: Verify CI integration 3ea85f0
    - [x] Confirm that a test PR triggers the CI and correctly pulls the image
- [x] Task: Conductor - User Manual Verification 'Workflow Migration' (Protocol in workflow.md) 961f11f

## Phase 3: Local Dev Parity & Cleanup [checkpoint: f36544e]

- [x] Task: Update local Dockerfile to extend the CI base image 61a7f9c
    - [x] Modify `docker/Dockerfile` to use `ghcr.io/inpalpra/pyprobe-ci:<version>` as its base
- [x] Task: Update Makefile for dynamic image tagging 9bc11bc
    - [x] Modify `Makefile` to read version from `.ci-version` and pass it as a build argument
- [x] Task: Verify local Docker execution
    - [x] Run `make verify-docker` and ensure it passes
- [x] Task: Conductor - User Manual Verification 'Local Dev Parity & Cleanup' (Protocol in workflow.md) f36544e
