Role: You are an expert Python Tooling Developer and DSP Engineer. You specialize in building high-performance developer tools that bridge the gap between scientific computing (MATLAB/LabVIEW) and Python software engineering.

The Goal: I want to build a "LabVIEW-style Variable Probe" for Python. In LabVIEW, you can click a "wire" (variable) while code is running and see a floating window that visualizes that data in real-time. I want to recreate this experience for debugging Python DSP scripts without modifying the original script heavily.

The Architecture: Create a standalone Python application (The "Probe Tool") that wraps and executes a target user script.

The Backend (The Runner):

Write a wrapper that executes a target Python script (e.g., user_script.py).

Use sys.settrace or a custom probe() hook function to intercept local variables during execution loops.

Critical Requirement: It must be able to "watch" specific variable names (e.g., symbols_I, filtered_signal).

The Frontend (The Visualizer):

Use PyQt6 for the window management.

Use PyQtGraph for the plotting (do NOT use Matplotlib, it is too slow for real-time DSP updates).

The UI should be a dark-themed "Dashboard" where I can type a variable name to "probe" it.

Smart Data Handling (The "DSP" Brain):

The tool must automatically detect the data type of the probed variable:

Case A (1D Array): If it's a standard list/numpy array, plot a Waveform Graph (Value vs Index).

Case B (Complex Array): If the data is complex (1j), plot a Constellation Diagram (Real on X-axis, Imaginary on Y-axis). This is crucial for my QPSK work.

Case C (Scalar): Just show the numerical value.

The "Vibe":

Think "Cyberpunk Instrument Panel."

Fast refresh rates.

Minimalist code structure so I can extend it later.

Rules:

Use ./.venv python virtual environment whenever running python commands. 