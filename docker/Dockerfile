ARG CI_VERSION=py3.12-qt6-v1
FROM ghcr.io/inpalpra/pyprobe-ci:${CI_VERSION}

WORKDIR /workspace

# Copy the entire project
COPY . .

# Install the project itself. 
# Since dependencies are already in the base image (baked in), 
# this will be extremely fast and should not require network access for dependencies.
RUN uv sync --frozen

# Build wheel inside clean OS
RUN uv build --wheel

CMD ["bash", "scripts/test_artifact.sh", "wheel"]
