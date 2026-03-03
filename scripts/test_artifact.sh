#!/usr/bin/env bash
set -e

MODE=${1:-wheel}

# In Docker/CI, we ALREADY have the full environment baked into the base image
# and synced in the Dockerfile. We do NOT want to create a new empty venv
# and reinstall everything from the network.

# If we are in Docker/CI, we use the pre-baked uv environment.
if [ -f /.dockerenv ] || [ "$CI" = "true" ]; then
    echo "Running in Docker/CI context. Using pre-baked dependencies."
    # The environment is already active or in the PATH from the base image.
else
    echo "Creating clean virtual environment for local testing..."
    python -m venv /tmp/test-env
    source /tmp/test-env/bin/activate
    pip install --upgrade pip
fi

if [ "$MODE" = "wheel" ]; then
    echo "Installing locally built wheel..."
    # We use pip to install the wheel into the current environment.
    # In Docker, this is the pre-baked environment.
    pip install dist/*.whl
elif [ "$MODE" = "pypi" ]; then
    echo "Installing wheel from PyPI..."
    pip install --force-reinstall pyprobe-plots
else
    echo "Unknown mode: $MODE"
    exit 1
fi

# NO MORE 'pip install pytest ...' HERE. It's in the base image.

echo "Creating isolated test workspace to prevent shadowing and repo dependencies..."
if [ -z "$CI" ] && [ ! -f /.dockerenv ]; then
    echo "Error: Refusing to create workspace outside of CI or Docker."
    exit 1
fi

TEST_WORKSPACE="/tmp/pyprobe-product-tests"
rm -rf "$TEST_WORKSPACE"
mkdir -p "$TEST_WORKSPACE"

cp -r tests "$TEST_WORKSPACE/"
cp -r scripts "$TEST_WORKSPACE/"
cp pyproject.toml "$TEST_WORKSPACE/" 2>/dev/null || true

echo "Switching to isolated workspace: $TEST_WORKSPACE"
cd "$TEST_WORKSPACE"

echo "Verifying import location..."
python - <<EOF
import pyprobe
print("pyprobe imported from:", pyprobe.__file__)
import os
assert "/workspace/pyprobe" not in pyprobe.__file__, "Shadowing detected! pyprobe imported from source."
EOF

# run_tests.sh will use the current environment's pytest
bash scripts/run_tests.sh
