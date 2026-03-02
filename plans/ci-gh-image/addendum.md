We’ll make your CI base image:
	•	✅ Multi-arch (linux/amd64 + linux/arm64)
	•	✅ Automatically rebuilt when docker/ci.Dockerfile changes
	•	✅ Versioned (py3.12-qt6-v1)
	•	✅ Properly cached with BuildKit
	•	✅ Published to GHCR
	•	✅ Zero manual rebuilds needed

This is the final, production-grade setup.

⸻

🧱 Your Image Tag

We’ll use:

ghcr.io/inpalpra/pyprobe-ci:py3.12-qt6-v1

If you change infra later → bump v1 → v2.

⸻

🐳 docker/ci.Dockerfile (unchanged)

⸻

🚀 FINAL: Automatic Multi-Arch Build Workflow

.github/workflows/build-ci-image.yml

name: Build CI Image (Multi-Arch)

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
      - name: Checkout
        uses: actions/checkout@v4

      # 1️⃣ Enable QEMU for cross-arch builds
      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      # 2️⃣ Enable Docker Buildx
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      # 3️⃣ Login to GHCR
      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      # 4️⃣ Build + Push multi-arch image
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/ci.Dockerfile
          platforms: linux/amd64,linux/arm64
          push: true
          tags: |
            ghcr.io/inpalpra/pyprobe-ci:py3.12-qt6-v1
          cache-from: type=gha
          cache-to: type=gha,mode=max


⸻

🧠 What This Does

When docker/ci.Dockerfile changes:
	1.	QEMU enables cross-arch building.
	2.	Buildx builds both:
	•	linux/amd64
	•	linux/arm64
	3.	A multi-arch manifest is pushed.
	4.	GitHub cache stores layers.
	5.	Future builds are much faster.

No manual build required ever again.

⸻

🧪 CI Usage (unchanged)

.github/workflows/ci.yml

GitHub runner automatically pulls amd64.

⸻

🐳 Local Usage (Apple Silicon)

Your Mac automatically pulls arm64.

No changes needed.

⸻

📦 Optional (Recommended): Add “latest” Tag Automatically

If you want both:
	•	versioned tag
	•	rolling latest

Modify tags: section to:

tags: |
  ghcr.io/inpalpra/pyprobe-ci:py3.12-qt6-v1
  ghcr.io/inpalpra/pyprobe-ci:latest
