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

echo "Removing source tree to prevent shadowing and repo dependencies..."
# WARNING: This script is intended for CI/Docker environments.
# Running this locally in your repo root will delete your source code.
if [ -z "$CI" ] && [ ! -f /.dockerenv ]; then
    echo "Error: Refusing to delete source tree outside of CI or Docker."
    echo "Use with caution or set CI=true if you really want this."
    exit 1
fi

# Clean up EVERYTHING that is not needed for running product tests.
# tests/ and scripts/ (needed to run the tests) are kept.
# pyproject.toml and uv.lock are also kept if needed, but not strictly by pytest.
rm -rf pyprobe pyprobe_tracer examples dev-tests regression \
       Makefile .git .github .agent .claude .vscode .pytest_cache .ruff_cache \
       gemini.md Dockerfile Dockerfile.test pyprobe.spec release.sh \
       CONSTITUTION.md CLAUDE.md README.md .proj2mdignore .gitignore .gitconfig .ci-version

find . -maxdepth 1 -name "*.egg-info" -exec rm -rf {} +
find . -maxdepth 1 -name "*.log" -exec rm -rf {} +

echo "Verifying import location..."
python - <<EOF
import pyprobe
print("pyprobe imported from:", pyprobe.__file__)
EOF

bash scripts/run_tests.sh
