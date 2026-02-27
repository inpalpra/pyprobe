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
- **Reference-Counted Graph Management:** Formal architecture for managing graph windows (w0, w1...) and their contained traces. Variables are automatically "unprobed" (highlights and icons removed) when no longer referenced in any active window.
- **Interactive Trace Control:** Easily remove specific traces via legend double-clicks or right-click context menus.
- **Global Trace IDs:** Unique tr<n> IDs for all probed variables for easy reference in equations.
- **Persistent Marker System:** Markers survive view/lens switches and application restarts.
- **Decoupled Tracer Architecture:** The debugger logic is decoupled from the GUI, running as a lightweight `pyprobe-tracer` package in a separate process for maximum stability and performance.
- Highly customizable themes (Cyberpunk, Monokai, Ocean).
- Real-time performance.
- **Structured Bug Reporting & Step Recording:** Built-in, non-blocking bug report system with optional step recording. Users can record all intentional UI interactions (probe lifecycle, overlays, lens changes, legend toggles, panel management, execution control, equation edits, etc.) and generate a structured report containing:
  - Ordered interaction history ("Steps to Reproduce")
  - Baseline session state snapshot
  - Open file metadata (with optional content inclusion)
  - Environment details (Python, PyProbe version, Qt version, platform, plugins, git commit)
  - Deterministic, sanitized paths (`<USER_HOME>` replacement)
  - Optional LLM-optimized formatting mode with line-numbered code and relevant code window extraction
  - The system is designed for forensic-grade reproducibility, enabling both human developers and LLMs to reliably reconstruct UI state transitions and diagnose complex interaction bugs.
 
## Engineering Philosophy
- **Deterministic Behavior First:** All state transitions are explicitly modeled and reproducible. No hidden side-effects. No silent state mutation.
- **Forensic-Grade Observability:** User-triggered interactions can be recorded with precise file/line/column identity, enabling exact reconstruction of UI state changes.
- **No Heuristic Rewriting of User Intent:** Bug reports preserve the user's description and interaction history verbatim. The system does not reinterpret, reclassify, or infer meaning.
- **Strict Separation of Concerns:** Debugger/tracer logic runs independently of the GUI to ensure stability, fault isolation, and performance.
- **Regression-Protected Evolution:** All core behavior (graph lifecycle, reference counting, recording, formatting) is guarded by permanent regression tests to prevent behavioral drift.
- **LLM-Aware but Human-First:** Reports are readable by engineers and optionally optimized for LLM consumption — without compromising honesty or structural integrity.
- **Zero-Loss Recording Principle:** If a user interaction mutates state or visuals, it should be observable and recordable.