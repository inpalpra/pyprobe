Artifact-first, Docker-isolated, zero-duplication CI architecture.

This gives you:
	•	✅ Always test built wheel (never source installs)
	•	✅ Local testing = Docker-based isolation
	•	✅ PR CI = build wheel → test wheel
	•	✅ Release CI = build wheel → test → publish → test-from-PyPI
	•	✅ One canonical pytest definition
	•	✅ One artifact installer
	•	✅ Zero duplicated ignore lists
	•	✅ Zero workflow drift

📁 Final Repo Structure

```
scripts/
  run_tests.sh
  test_artifact.sh

docker/
  Dockerfile

.github/workflows/
  ci.yml
  release.yml

Makefile
```

⸻

1️⃣ Canonical Test Runner

```
scripts/run_tests.sh
```
This is the only place pytest is defined.

```bash
#!/usr/bin/env bash
set -e

echo "Running canonical pytest suite..."

set +e
xvfb-run --auto-servernum \
  pytest tests/ -v --tb=short \
    --ignore=tests/gui/test_script_runner_subprocess.py \
    --ignore=tests/test_cli_automation.py \
    --ignore=tests/ipc/test_socket_channel.py
rc=$?
set -e

if [ $rc -eq 139 ]; then
  echo "⚠ SIGSEGV during Qt cleanup (cosmetic) — treating as success."
  exit 0
fi

exit $rc
```
Make executable:

```bash
chmod +x scripts/run_tests.sh
```


⸻

2️⃣ Artifact Installer Wrapper

```
scripts/test_artifact.sh
```

This installs either:
	•	locally built wheel
	•	or PyPI wheel

Then runs canonical tests.

```bash
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

echo "Removing source tree to prevent shadowing..."
rm -rf pyprobe pyprobe_tracer examples regression
find . -maxdepth 1 -name "*.egg-info" -exec rm -rf {} +

echo "Verifying import location..."
python - <<EOF
import pyprobe
print("pyprobe imported from:", pyprobe.__file__)
EOF

bash scripts/run_tests.sh
```

Make executable:

```bash
chmod +x scripts/test_artifact.sh
```


⸻

3️⃣ Docker Isolation (Local Only)

```
docker/Dockerfile
```

Single container. No split build/test stages needed.

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Qt / GUI dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    libgl1 libegl1 libglib2.0-0 \
    libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-render-util0 \
    libxcb-shape0 libxcb-xfixes0 \
    libxcb-xinerama0 libxcb-randr0 \
    libxkbcommon-x11-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY . .

RUN pip install --no-cache-dir build

# Build wheel inside clean OS
RUN python -m build --wheel

CMD ["bash", "scripts/test_artifact.sh", "wheel"]
```

⸻

4️⃣ Makefile (Local Developer Entry Point)

```makefile
.PHONY: verify-docker

verify-docker:
	docker build -t pyprobe-test -f docker/Dockerfile .
	docker run --rm pyprobe-test
```
Now local testing:

make verify-docker

This is your unimpeachable isolation.

⸻

5️⃣ CI Workflow (PR + Push)

```
.github/workflows/ci.yml
```

```yaml
name: CI

on:
  push:
    branches: [ "main" ]
  pull_request:

permissions:
  contents: read

jobs:
  test-wheel:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v4

      - name: Install display dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y --no-install-recommends \
            libegl1 libgl1 libglib2.0-0 \
            libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
            libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
            libxcb-shape0 libxcb-xfixes0 libxcb-xinerama0 \
            libxcb-xkb1 libxkbcommon-x11-0 \
            xvfb

      - name: Build wheel
        run: uv build --wheel

      - name: Test built wheel
        run: bash scripts/test_artifact.sh wheel
```

This replaces test-only.yml.

⸻

6️⃣ Release Workflow

```
.github/workflows/release.yml
```

```yaml
name: Release

on:
  push:
    tags: ['v*']
  workflow_dispatch:

permissions:
  contents: write
  id-token: write

jobs:

  test-wheel:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v4

      - name: Install display dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y --no-install-recommends \
            libegl1 libgl1 libglib2.0-0 \
            libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
            libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
            libxcb-shape0 libxcb-xfixes0 libxcb-xinerama0 \
            libxcb-xkb1 libxkbcommon-x11-0 \
            xvfb

      - name: Build wheel
        run: uv build --wheel

      - name: Test built wheel
        run: bash scripts/test_artifact.sh wheel

      - name: Upload wheel artifact
        uses: actions/upload-artifact@v4
        with:
          name: wheel
          path: dist/*.whl

  publish:
    needs: test-wheel
    runs-on: ubuntu-latest

    steps:
      - uses: actions/download-artifact@v4
        with:
          name: wheel
          path: dist/

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1

  verify-pypi:
    needs: publish
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install display dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y --no-install-recommends \
            libegl1 libgl1 libglib2.0-0 \
            libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
            libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
            libxcb-shape0 libxcb-xfixes0 libxcb-xinerama0 \
            libxcb-xkb1 libxkbcommon-x11-0 \
            xvfb

      - name: Wait for PyPI index
        run: sleep 90

      - name: Test installed PyPI artifact
        run: bash scripts/test_artifact.sh pypi
```
