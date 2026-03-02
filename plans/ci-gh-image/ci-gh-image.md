⸻

✅ FINAL FINAL ARCHITECTURE (Versioned Images)

We’ll use:

ghcr.io/inpalpra/pyprobe-ci:py3.12-qt6-v1

You bump v1 → v2 when:
	•	system libs change
	•	python version changes
	•	CI base changes

⸻

📁 Final Structure

docker/
  ci.Dockerfile
  Dockerfile   (local test image, extends ci image)

scripts/
  run_tests.sh
  test_artifact.sh

.github/workflows/
  build-ci-image.yml
  ci.yml
  release.yml

Makefile


⸻

🐳 1️⃣ Versioned CI Base Image

docker/ci.Dockerfile

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---- System runtime deps (Qt6 compatible) ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    libgl1 libegl1 libglib2.0-0 \
    libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-render-util0 \
    libxcb-shape0 libxcb-xfixes0 \
    libxcb-xinerama0 libxcb-randr0 \
    libxkbcommon-x11-0 \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ---- Stable Python tooling layer ----
RUN pip install --no-cache-dir \
    build \
    pytest \
    pytest-qt \
    pytest-xdist \
    pytest-forked

WORKDIR /workspace


⸻

🚀 2️⃣ Build and Push Versioned Image

Run once:

docker build \
  -t ghcr.io/inpalpra/pyprobe-ci:py3.12-qt6-v1 \
  -f docker/ci.Dockerfile .

docker push ghcr.io/inpalpra/pyprobe-ci:py3.12-qt6-v1

Optional convenience tag:

docker tag \
  ghcr.io/inpalpra/pyprobe-ci:py3.12-qt6-v1 \
  ghcr.io/inpalpra/pyprobe-ci:latest

docker push ghcr.io/inpalpra/pyprobe-ci:latest

Now you have immutable + moving tag.

⸻

🔁 3️⃣ Auto Rebuild CI Image (Versioned)

.github/workflows/build-ci-image.yml

name: Build CI Image

on:
  push:
    paths:
      - docker/ci.Dockerfile
  workflow_dispatch:

permissions:
  contents: read
  packages: write

jobs:
  build-and-push:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Login to GHCR
        run: echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin

      - name: Build image
        run: |
          docker build \
            -t ghcr.io/inpalpra/pyprobe-ci:py3.12-qt6-v1 \
            -f docker/ci.Dockerfile .

      - name: Push image
        run: docker push ghcr.io/inpalpra/pyprobe-ci:py3.12-qt6-v1

When you need a base change:
	•	Change tag to v2
	•	Update workflows
	•	Done

⸻

🧪 4️⃣ CI Workflow (PR + Push)

.github/workflows/ci.yml

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
    container:
      image: ghcr.io/inpalpra/pyprobe-ci:py3.12-qt6-v1

    steps:
      - uses: actions/checkout@v4

      - name: Build wheel
        run: python -m build --wheel

      - name: Test built wheel
        run: bash scripts/test_artifact.sh wheel

Zero apt installs.
Zero pytest installs.
Minimal bandwidth.

⸻

🚀 5️⃣ Release Workflow (Versioned Container)

.github/workflows/release.yml

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
    container:
      image: ghcr.io/inpalpra/pyprobe-ci:py3.12-qt6-v1

    steps:
      - uses: actions/checkout@v4

      - name: Build wheel
        run: python -m build --wheel

      - name: Test built wheel
        run: bash scripts/test_artifact.sh wheel

      - name: Upload wheel
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
    container:
      image: ghcr.io/inpalpra/pyprobe-ci:py3.12-qt6-v1

    steps:
      - uses: actions/checkout@v4

      - name: Wait for PyPI index
        run: sleep 90

      - name: Test installed PyPI artifact
        run: bash scripts/test_artifact.sh pypi


⸻

🐳 6️⃣ Local Docker (Extends Versioned CI Base)

docker/Dockerfile

FROM ghcr.io/inpalpra/pyprobe-ci:py3.12-qt6-v1

WORKDIR /workspace
COPY . .

RUN python -m build --wheel

CMD ["bash", "scripts/test_artifact.sh", "wheel"]

Local test:

make verify-docker

Now local + CI share identical runtime.

⸻

🧠 When To Bump Image Version

Bump v1 → v2 if:
	•	Python version changes
	•	Major Qt generation changes
	•	You add system deps
	•	CI base needs update

Do NOT bump for:
	•	Normal dependency bumps
	•	PyPI version bumps
	•	Project code changes

