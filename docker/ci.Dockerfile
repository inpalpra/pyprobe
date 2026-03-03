FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT=/usr/local/uv-env
ENV PATH="$UV_PROJECT_ENVIRONMENT/bin:$PATH"

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
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /workspace

# Copy dependency manifests
COPY pyproject.toml uv.lock ./

# Pre-install ALL dependencies into a global-ish environment
# We use --no-install-project because we only want the dependencies in the base image.
RUN uv sync --frozen --no-install-project --all-groups

# Ensure the environment is usable by downstream
RUN chmod -R a+rx $UV_PROJECT_ENVIRONMENT
