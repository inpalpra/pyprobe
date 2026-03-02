#!/usr/bin/env bash
# verify-artifact.sh — Build and verify the pyprobe wheel in isolated Docker containers.
#
# Usage:
#   ./scripts/verify-artifact.sh

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# Paths
BUILD_DOCKERFILE="docker/build.Dockerfile"
TEST_DOCKERFILE="docker/test.Dockerfile"
DIST_DIR="dist"
BUILD_IMAGE="pyprobe-build"
TEST_IMAGE="pyprobe-test"

# Function to print section headers
header() {
    echo -e "
${CYAN}${BOLD}=== $1 ===${RESET}"
}

# 1. Build Stage A (Build Container)
header "Building Stage A: Build Container"
docker build -t "$BUILD_IMAGE" -f "$BUILD_DOCKERFILE" .

# 2. Extract artifact
header "Extracting Built Wheel"
# Create a temporary container to copy the artifact out
CONTAINER_ID=$(docker create "$BUILD_IMAGE")

# Ensure cleanup of the temporary container
trap 'docker rm -f $CONTAINER_ID >/dev/null 2>&1' EXIT

# Clean local dist/ directory
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

# Copy the wheel from the container
docker cp "$CONTAINER_ID:/workspace/dist/." "$DIST_DIR/"

echo -e "${GREEN}✓ Artifact extracted to $DIST_DIR/${RESET}"
ls -lh "$DIST_DIR"

# 3. Build Stage B (Test Container)
if [[ -f "$TEST_DOCKERFILE" ]]; then
    header "Building Stage B: Test Container"
    docker build -t "$TEST_IMAGE" -f "$TEST_DOCKERFILE" .

    header "Running Isolated Tests"
    # Run the test container under Xvfb for GUI tests
    docker run --rm "$TEST_IMAGE"
    echo -e "${GREEN}✓ All tests passed in isolated environment!${RESET}"
else
    echo -e "${YELLOW}Stage B Dockerfile not found yet, skipping test phase.${RESET}"
fi

echo -e "
${GREEN}${BOLD}Verification Complete!${RESET}"
