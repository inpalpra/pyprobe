# PyProbe Plots Product Guide

## Initial Concept
PyProbe Plots is a powerful, visual, variable-probing debugger designed specifically for Python Digital Signal Processing (DSP) development. It bridges the gap between traditional logic-stepping debuggers and complex mathematical array visualizations.

## Target Audience
- Python Developers working on DSP algorithms.
- Data Scientists and Researchers analyzing temporal states.
- Engineers needing real-time visualization of complex numerical arrays.

## Key Goals
- **Instant Visualization:** Enable rendering of complex numerical arrays seamlessly.
- **Time-Aware Debugging:** Allow stepping through code while observing signal evolution.
- **Zero-Friction UI:** Provide a dockable, highly customizable interface via PyQtGraph and PyQt6.
- **Non-Intrusive API:** Debug math without having to rewrite or modify the core algorithms.

## Core Features
- Built-in support for waveforms (real/imag/mag/phase).
- Constellation diagrams and scalar histories.
- **Equation Editor:** Perform real-time mathematical operations on raw probed data (traces) using Python-based expressions (numpy/scipy).
- **Global Trace IDs:** Unique tr<n> IDs for all probed variables for easy reference in equations.
- **Persistent Marker System:** Markers survive view/lens switches and application restarts.
- Highly customizable themes (Cyberpunk, Monokai, Ocean).
- Real-time performance.