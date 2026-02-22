# PyProbe Plots

[![PyPI version](https://badge.fury.io/py/pyprobe-plots.svg)](https://badge.fury.io/py/pyprobe-plots)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**PyProbe Plots** is a powerful, visual, variable-probing debugger designed specifically for Python Digital Signal Processing (DSP) development.

Traditional debuggers are great for stepping through logic, but DSP algorithms often deal with massive arrays of complex numbers, temporal state across loop iterations, and abstract transformations that are impossible to parse mentally from numerical text outputs.

PyProbe bridges this gap by providing a rich, real-time GUI that instantly visualizes waveforms, constellations, scalar histories, and more, exactly where the variables live in your source code.

## Features

- **Instant Visualization**: Probe any variable and watch it render instantly as a rich plot.
- **DSP-Focused**: Built-in support for waveforms (real/imag/mag/phase), constellation diagrams, and scalar histories.
- **Time-Aware Debugging**: Step through your code and watch the plots evolve in sequence.
- **Zero-Friction UI**: Dockable workspace, highly customizable themes (Cyberpunk, Monokai, Ocean), and high-performance rendering via PyQtGraph.
- **Seamless Integration**: Non-intrusive APIs mean you don't have to rewrite your math to debug it.

## Installation

```bash
pip install pyprobe-plots
```

## Quick Start

```python
from pyprobe import probe
import numpy as np

# Generate a simple noisy sine wave
t = np.linspace(0, 1, 500)
signal = np.sin(2 * np.pi * 10 * t)
noise = np.random.normal(0, 0.2, len(t))

noisy_signal = signal + noise

# Probe it directly to see the plot pop up!
probe(noisy_signal, title="Noisy Sine Wave")
```

*(Note: Documentation and full API are currently actively expanding!)*

## Screenshots

<p align="center">
  <img src="https://github.com/user-attachments/assets/90bd59c3-8b73-461f-afce-73a411ce0f52" alt="PyProbe Interface showing multiple docked DSP plots" width="800"/>
</p>

## License

MIT License
