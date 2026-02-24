# PyProbe Plots Tech Stack

## Programming Language
- **Python (>=3.12):** The core language, chosen for its vast ecosystem in scientific computing and DSP.

## Frontend UI / Visualization
- **PyQt6:** The primary framework for building the desktop application GUI, providing native-like interfaces and robust window management.
- **pyqtgraph:** The high-performance plotting library used for rendering real-time graphs, constellation diagrams, and waveforms. It provides the core visual engine capable of handling dense datasets efficiently.

## Data Processing & Mathematics
- **NumPy:** Essential for handling large N-dimensional arrays of complex and real numbers representing signals and states.
- **SciPy:** Used for advanced DSP algorithms, filtering, and mathematical operations.
- **Matplotlib:** Available as an auxiliary plotting tool, though pyqtgraph is the primary engine for real-time performance.

## Build & Testing
- **pytest:** The primary testing framework.
- **pytest-qt:** For testing PyQt6 components.
- **setuptools / uv:** For packaging and dependency management.