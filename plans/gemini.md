Here is the strategic roadmap for PyProbe.

### 1. Long Term Vision

**"The Digital Oscilloscope for Python Code"**

* **Current State:** A variable watch window with plots.
* **Future State:** A sidecar instrument panel. You code in IDE. You probe in PyProbe.
* **The Feeling:** LabVIEW for text.
* Click line -> See signal.
* No print statements.
* No `matplotlib.show()`.

### 2. Next Milestones

**Milestone 1: The "Click" (Source Anchoring)**

* **Goal:** Kill manual typing of variable names.
* **Tech:** Add read-only Code View to PyProbe.
* **Feature:** User clicks `x` in code view -> `x` plots instantly.
* **Backend:** Map `(file, line, col)` to `local_variable`.

**Milestone 2: The "Lens" (Plugin System)**

* **Goal:** One variable, many views.
* **Problem:** Complex array  always constellation.
* **Feature:** Right-click probe -> "View As..." (Spectrum, Histogram, IQ, Image).
* **Tech:** Stable `Visualizer` API.

**Milestone 3: The "DVR" (Time Travel)**

* **Goal:** Inspect past without restarting.
* **Feature:** Pause. Scrub slider back 500 frames. See data then.
* **Tech:** Ring buffer in shared memory.

### 3. Recommended User Workflow

Two-window setup:

1. **Left Screen:** VS Code / Neovim / PyCharm. (Write code).
2. **Right Screen:** PyProbe. (See signals).

**The Loop:**

1. Edit code in IDE. Save.
2. PyProbe auto-reloads.
3. Click interesting line in PyProbe.
4. Waveforms dance.
5. Spot bug. Repeat.

### 4. Tech Stack

Keep it simple. Don't add web bloat.

* **GUI:** PyQt6 (Native speed, great for high-FPS plots).
* **Plotting:** pyqtgraph (OpenGL accelerated). **Critical for DSP.**
* **Runtime:** `sys.settrace` (CPython standard).
* **Analysis:** `ast` module (Static analysis to find variables on lines).
* **IPC:** `multiprocessing.shared_memory` (Zero-copy for big arrays).

### 5. Architecture

Split the brain (GUI) from the muscle (Runner).

```ascii
+---------------------+          +----------------------+
|   GUI PROCESS       |          |   RUNNER PROCESS     |
| (PyQt6 + Plots)     |          | (User Script)        |
+---------------------+          +----------------------+
|                     |          |                      |
| [ Code Viewer ]     |          |  [ User Code ]       |
|   | (Static AST)    |          |       ^              |
|   v                 |          |       |              |
| [ Probe Manager ] --|--Cmds--->|  [ Tracer ]          |
|   ^                 |          |    (sys.settrace)    |
|   |                 |          |       |              |
| [ Visualizers ]     |          |       v              |
|   ^                 |<--Data---|  [ IPC / ShMem ]     |
|   |                 |          |                      |
+---|-----------------+          +----------------------+
    |
[ Plugin API ]

```

### 6. The "Glue" (Foundations)

These must be rock solid. Do not break these later.

**A. The Address System (Data Model)**
Variables change. Addresses stay.

* **Bad:** `name="x"` (Functions have many `x`s).
* **Good:** `ProbeID(file_path, line_no, func_name, var_name)`.
* *Why:* Allows probing distinct instances of variables across recursive calls or loops.

**B. The Plugin Interface (API)**
Allow users to write their own scopes.

```python
class VisualizerPlugin:
    def can_handle(dtype, shape): bool
    def update(data_buffer): void
    def render(plot_item): void

```

**C. The Ring Buffer (Data Structure)**

* Don't stream every float.
* Write to circular buffer in Shared Memory.
* GUI reads at 60Hz.
* Runner writes at 10kHz.
* Decouples execution speed from display speed.

### Next Step

Would you like me to sketch out the **Python `ast` logic** required to map a "click on line 10" to "variable name `sig_out`", which is the prerequisite for Milestone 1?