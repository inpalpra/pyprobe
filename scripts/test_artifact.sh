#!/usr/bin/env bash
set -e

MODE=${1:-wheel}

echo "Creating clean virtual environment..."
python -m venv /tmp/test-env
source /tmp/test-env/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

if [ "$MODE" = "wheel" ]; then
    echo "Installing locally built wheel..."
    pip install dist/*.whl
elif [ "$MODE" = "pypi" ]; then
    echo "Installing wheel from PyPI..."
    pip install pyprobe-plots
else
    echo "Unknown mode: $MODE"
    exit 1
fi

echo "Installing test dependencies..."
pip install pytest pytest-qt pytest-xdist pytest-forked

echo "Creating isolated test workspace to prevent shadowing and repo dependencies..."
# WARNING: This script is intended for CI/Docker environments.
if [ -z "$CI" ] && [ ! -f /.dockerenv ]; then
    echo "Error: Refusing to create workspace outside of CI or Docker."
    exit 1
fi

TEST_WORKSPACE="/tmp/pyprobe-product-tests"
rm -rf "$TEST_WORKSPACE"
mkdir -p "$TEST_WORKSPACE"

# Copy ONLY what is strictly needed for running product tests.
cp -r tests "$TEST_WORKSPACE/"
cp -r scripts "$TEST_WORKSPACE/"
cp pyproject.toml "$TEST_WORKSPACE/" 2>/dev/null || true

echo "Switching to isolated workspace: $TEST_WORKSPACE"
cd "$TEST_WORKSPACE"

echo "Verifying import location..."
python - <<EOF
import pyprobe
print("pyprobe imported from:", pyprobe.__file__)
# Ensure it's NOT importing from the original workspace
import os
assert "/workspace/pyprobe" not in pyprobe.__file__, "Shadowing detected! pyprobe imported from source."
EOF

bash scripts/run_tests.sh
