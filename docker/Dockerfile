ARG CI_VERSION=py3.12-qt6-v2
FROM ghcr.io/inpalpra/pyprobe-ci:${CI_VERSION}

WORKDIR /workspace

# Copy only metadata for a cached install layer if possible
COPY pyproject.toml uv.lock ./

# Copy the entire project
COPY . .

# Install the project itself globally (no venv) to avoid shadowing and symlink issues.
# --no-deps ensures we don't try to re-download anything already in the base.
RUN pip install --no-cache-dir --no-deps .

# Build wheel inside clean OS
# We still want the wheel for artifact testing.
RUN uv build --wheel

CMD ["bash", "scripts/test_artifact.sh", "wheel"]
