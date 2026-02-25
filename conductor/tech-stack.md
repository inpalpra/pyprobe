# PyProbe Plots Tech Stack

## Programming Language
- **Python (>=3.12):** The core language, chosen for its vast ecosystem in scientific computing and DSP.

## Frontend UI / Visualization
- **PyQt6:** The primary framework for building the desktop application GUI, providing native-like interfaces and robust window management.
- **PyQt6.sip:** Used for low-level interaction with C++ objects and safe object validity checking (isdeleted).
- **pyqtgraph:** The high-performance plotting library used for rendering real-time graphs, constellation diagrams, and waveforms. It provides the core visual engine capable of handling dense datasets efficiently.

## Data Processing & Mathematics
- **NumPy:** Essential for handling large N-dimensional arrays of complex and real numbers representing signals and states.
- **SciPy:** Used for advanced DSP algorithms, filtering, and mathematical operations.
- **Matplotlib:** Available as an auxiliary plotting tool, though pyqtgraph is the primary engine for real-time performance.

## Build & Testing
- **pytest:** The primary testing framework.
- **pytest-qt:** For testing PyQt6 components.
- **setuptools / uv:** For packaging and dependency management.

## IPC & Subprocess Management
- **Socket-based IPC:** A custom bidirectional protocol using TCP sockets for reliable communication between the GUI and the tracer.
- **Wire Protocol:** A high-performance serialization layer using JSON for structure and raw binary for numerical arrays (NumPy).
- **pyprobe-tracer:** A lightweight, standalone package injected into the user's script process to capture variables without GUI dependencies.