ARG CI_VERSION=py3.12-qt6-v1
FROM ghcr.io/inpalpra/pyprobe-ci:${CI_VERSION}

WORKDIR /workspace
COPY . .

# Build wheel inside clean OS
RUN python -m build --wheel

CMD ["bash", "scripts/test_artifact.sh", "wheel"]
