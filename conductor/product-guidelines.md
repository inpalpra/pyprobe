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

## 5. Strict TDD for PyQt6
To maintain stability in a complex GUI environment, we follow a strict TDD lifecycle for every feature and bug fix:

### 5.1 The Red Phase (GUI)
- **Create a reproduction test:** For bugs, create a test that fails by asserting the *visual* state of the widget (e.g., "curve should have 100 points but has 0").
- **E2E Probe Injection:** For new features, use the `win` fixture and inject data via `win._on_probe_value(payload)` to simulate real user data flow.
- **Synchronization:** Always call `qapp.processEvents()` after injecting data or triggering actions.

### 5.2 The Green Phase (GUI)
- Implement only what is needed to make the `pytest-qt` assertions pass.
- Use `QTest.keyPress` or `QTest.mouseClick` to simulate user interaction during implementation if needed.

### 5.3 Automated E2E Patterns
Every new GUI feature must include an E2E test in `tests/gui/` that follows this pattern:
1. **Setup:** Create a `MainWindow` or target `Widget` using a fixture.
2. **Action:** Inject data or trigger a UI event (shortcut, click).
3. **Wait:** `qapp.processEvents()` to allow the event loop to flush.
4. **Inspect:** Assert against the low-level rendering objects (e.g., `pg.PlotCurveItem`, `pg.ScatterPlotItem`) or widget properties.
5. **Visibility:** Verify that components are visible/hidden as expected using `.isVisible()`.