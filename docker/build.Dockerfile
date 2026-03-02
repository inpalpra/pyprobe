# Stage A: Build Container
FROM python:3.12-slim

# Prevent python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

# Install system build dependencies if any (none for pure python usually, but build needs build)
RUN pip install --no-cache-dir build

# Copy dependency manifests first for better layer caching
COPY pyproject.toml uv.lock* requirements*.txt ./

# Install project dependencies (optional for build stage, but good for validation)
# Since we are building a wheel, 'build' will handle dependencies listed in pyproject.toml

# Copy the rest of the source tree
COPY . .

# Build the wheel
RUN python -m build --wheel

# The artifact is now in /workspace/dist/
