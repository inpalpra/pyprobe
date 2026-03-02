FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---- System runtime deps (Qt6 compatible) ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb xauth \
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
