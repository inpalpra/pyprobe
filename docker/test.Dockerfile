# Stage B: Test Container
FROM python:3.12-slim

# Prevent python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for GUI testing (Xvfb + Qt deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    libgl1 \
    libegl1 \
    libdbus-1-3 \
    libxkbcommon-x11-0 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxcb-randr0 \
    libfontconfig1 \
    libxrender1 \
    libxi6 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m appuser
WORKDIR /workspace

# Create virtual environment in a location accessible by appuser
RUN python -m venv /verify-env
ENV PATH="/verify-env/bin:$PATH"

# Copy the built wheel from the local dist/ directory
COPY dist/*.whl .

# Install the wheel and test dependencies
RUN pip install --no-cache-dir *.whl pytest pytest-qt pytest-forked numpy scipy pyqt6 pyqtgraph

# Copy test suites and examples (NOT the source package pyprobe/)
COPY tests/ ./tests/
COPY examples/ ./examples/
COPY pyproject.toml . 

# Ensure the source package pyprobe/ is NOT present to avoid shadowing
RUN if [ -d "pyprobe" ]; then echo "Error: source package pyprobe/ found in test container!" && exit 1; fi

# Change ownership to non-root user
RUN chown -R appuser:appuser /workspace /verify-env

USER appuser

# Set up Xvfb display
ENV DISPLAY=:99

# Default command: start Xvfb and run pytest
CMD ["sh", "-c", "Xvfb :99 -screen 0 1280x1024x24 & sleep 2 && pytest"]
