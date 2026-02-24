# PyProbe Plots Product Guidelines

## 1. Design Philosophy
- **Functionality First:** The primary goal is to provide accurate, real-time DSP data visualization. Design elements should enhance data readability rather than distract from it.
- **Low Friction:** Debugging tools should be intuitive. Avoid requiring deep configuration or complex setups just to see a basic plot. The `probe()` API should remain clean and non-intrusive.

## 2. User Experience (UX) Principles
- **Responsiveness:** The UI must remain responsive even when handling massive datasets or high-frequency updates. Render loops must be optimized to prevent blocking the main thread.
- **Clarity in Complexity:** Complex data structures like multi-dimensional arrays or constellation diagrams must be presented as clearly as possible using appropriate visual tools (color mapping, markers, grids).
- **Graceful Failure:** If an invalid data type is probed, the debugger should handle it gracefully without crashing the target application. Provide helpful error messages.

## 3. Visual & Aesthetic Guidelines
- **Themes:** Support multiple themes (Cyberpunk, Monokai, Ocean) to accommodate different user preferences and environments.
- **High Contrast:** Ensure plotted data has high contrast against the background for immediate visibility.
- **Data Density:** Use scalable components (via PyQtGraph) that can handle dense data point concentrations seamlessly (e.g., using downsampling when zoomed out).

## 4. Documentation & Communication
- **API Documentation:** The API should be self-documenting as much as possible, supported by clear docstrings with examples.
- **Tutorials:** Provide concise examples showcasing how to debug specific DSP scenarios (e.g., waveforms vs. constellations).
- **Prose Style:** Use direct, professional language in documentation. Focus on the 'why' and 'how' for DSP engineers.