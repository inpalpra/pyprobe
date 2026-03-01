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
- **Unambiguous Trace Nomenclature:** Formal naming system for trace components (e.g., `tr0.real`, `tr1.mag_db`) that persists across view switches and legend entries, providing absolute forensic clarity in reports and equations.
- **Reference-Counted Graph Management:** Formal architecture for managing graph windows (w0, w1...) and their contained traces. Variables are automatically "unprobed" (highlights and icons removed) when no longer referenced in any active window.
- **Synchronized Multi-Axis Interaction:** Dual-axis lenses (FFT, Mag/Phase) employ proportional vertical synchronization, ensuring that panning or zooming one axis updates the other relative to its own scale and units.
- **Global Signal Color Consistency:** Automatic synchronization of probe colors across all windows and overlays, maintaining visual identity for every signal regardless of where it is plotted.
- **Intelligent Zoom-Responsive Downsampling:** High-performance rendering for massive datasets that dynamically switches between downsampled and raw data based on the visible range, ensuring both rapid panning and forensic detail.
- **Stable Zoom Reset:** Immediate, flicker-free return to full data view via synchronized curve restoration and axis unpinning, preventing range drift and incremental widening.
- **Interactive Trace Control:** Easily remove specific traces via legend double-clicks or right-click context menus.
- **Global Trace IDs:** Unique tr<n> IDs for all probed variables for easy reference in equations.
- **Persistent Marker System:** Markers survive view/lens switches and application restarts.
- **Decoupled Tracer Architecture:** The debugger logic is decoupled from the GUI, running as a lightweight `pyprobe-tracer` package in a separate process for maximum stability and performance.
- **Technical Typography:** High-legibility monospaced interface (`JetBrains Mono`) across all themes, optimized for rapid parsing of numerical data, signal names, and source code.
- Highly customizable themes (Cyberpunk, Monokai, Ocean, Anthropic).
- Real-time performance.
- **Structured Bug Reporting & Step Recording:** Built-in, non-blocking bug report system with optional step recording. Users can record all intentional UI interactions (probe lifecycle, overlays, lens changes, legend toggles, panel management, execution control, equation edits, etc.) and generate a structured report containing:
  - Ordered interaction history ("Steps to Reproduce") with unambiguous interaction vocabulary (e.g., "Panned Horizontal axis directly").
  - Baseline session state snapshot including detailed window hierarchies (docked/visible status), active lens configurations, and explicit legend entries.
  - Open file metadata (with optional content inclusion)
  - Environment details (Python, PyProbe version, Qt version, platform, plugins, git commit)
  - Deterministic, sanitized paths (`<USER_HOME>` replacement)
  - Optional LLM-optimized formatting mode with line-numbered code and relevant code window extraction
  - The system is designed for forensic-grade reproducibility, tracking precise probe locations (`symbol @ file:line:col`) and providing a 1:1 mapping between visible legend items and report metadata.
 
## Engineering Philosophy
- **Deterministic Behavior First:** All state transitions are explicitly modeled and reproducible. No hidden side-effects. No silent state mutation.
- **Forensic-Grade Observability:** User-triggered interactions can be recorded with precise file/line/column identity, enabling exact reconstruction of UI state changes.
- **No Heuristic Rewriting of User Intent:** Bug reports preserve the user's description and interaction history verbatim. The system does not reinterpret, reclassify, or infer meaning.
- **Strict Separation of Concerns:** Debugger/tracer logic runs independently of the GUI to ensure stability, fault isolation, and performance.
- **Regression-Protected Evolution:** All core behavior (graph lifecycle, reference counting, recording, formatting) is guarded by permanent regression tests to prevent behavioral drift.
- **LLM-Aware but Human-First:** Reports are readable by engineers and optionally optimized for LLM consumption — without compromising honesty or structural integrity.
- **Zero-Loss Recording Principle:** If a user interaction mutates state or visuals, it should be observable and recordable.