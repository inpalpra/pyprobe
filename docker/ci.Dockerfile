FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---- System runtime deps (Qt6 compatible) ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb xauth \
    libgl1 libegl1 libglib2.0-0 \
    libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
    libxcb-shape0 libxcb-xfixes0 \
    libxcb-xinerama0 libxcb-xkb1 \
    libxkbcommon-x11-0 \
    libfontconfig1 libxrender1 libxext6 \
    libdbus-1-3 \
    build-essential \
    ca-certificates \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /workspace

# Copy dependency manifests
COPY pyproject.toml uv.lock ./

# Install ALL dependencies into the SYSTEM site-packages.
# This makes them available to any python process (including pip inside test_artifact.sh)
# without needing a virtualenv.
RUN uv export --frozen --all-groups --no-hashes > requirements.txt && \
    uv pip install --system --requirement requirements.txt && \
    rm requirements.txt
