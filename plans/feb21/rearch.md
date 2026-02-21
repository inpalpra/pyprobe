# PyProbe Rearchitecture: Split into GUI Binary + `pyprobe-tracer` Pip Package

## Context: What is PyProbe?

PyProbe is an interactive variable-probing debugger for Python DSP development. Users hover over variables in a code viewer, click to create probes, and see live visualizations (waveforms, constellations, scalar histories) update as the target script executes. It is a PyQt6 + pyqtgraph GUI application.

The project lives at `/Users/ppal/repos/pyprobe`. Read `CLAUDE.md` and `CONSTITUTION.md` for the full design philosophy and architecture overview.

## The Problem

PyProbe currently runs as **two processes** connected via `multiprocessing`:

1. **GUI process** (PyQt6) — code viewer, probe panels, plot rendering
2. **Runner subprocess** — spawned via `multiprocessing.Process(target=run_script_subprocess)`, executes the target script with `sys.settrace` hooks to capture probed variables

IPC uses `multiprocessing.Queue` for commands and small data, and `multiprocessing.shared_memory` for large numpy arrays.

This architecture has a **fatal flaw for standalone distribution**:

- We ship PyProbe as a standalone executable via PyInstaller (see `.github/workflows/release.yml` and `pyprobe.spec`).
- In the frozen PyInstaller binary, `multiprocessing.Process` spawns a child that re-executes the **frozen binary's entry point**. The child process runs inside PyProbe's **bundled Python 3.12 interpreter** — not the user's Python.
- This means the target script can only import packages that PyInstaller bundled with PyProbe (`numpy`, `scipy`, `matplotlib`, `PyQt6`, `pyqtgraph`).
- If the user's script needs `pandas`, `torch`, `scikit-learn`, or any other package, it will crash with `ImportError`.
- The user's scripts may also require a different Python version (e.g., 3.10, 3.13), which the frozen binary cannot provide.

**In short**: the current architecture couples PyProbe's Python environment to the target script's Python environment. For a standalone debugger tool, these must be decoupled.

## The Solution: Option C — Standalone GUI + Separate `pyprobe-tracer` Package

Split PyProbe into two independently distributable components:

### 1. `pyprobe` (standalone GUI binary)

- Distributed as a PyInstaller executable (macOS, Linux, Windows) via GitHub Releases
- Contains the entire GUI: code viewer, probe panels, plot rendering, theme system
- Does **not** execute the target script itself
- Launches the tracer in the **user's Python interpreter** via `subprocess.Popen`
- Communicates with the tracer over a new cross-process IPC mechanism (e.g., TCP socket, Unix socket, or `multiprocessing.connection` over sockets)

### 2. `pyprobe-tracer` (pip package)

- Lightweight pip-installable package: `pip install pyprobe-tracer`
- Contains only the tracing engine (`sys.settrace` hooks, `CaptureManager`, `VariableTracer`, `ProbeAnchor`, `DataClassifier`, etc.)
- Contains an IPC client that connects back to the GUI and sends captured data
- Entry point: `python -m pyprobe_tracer <script.py>` (launched by the GUI binary)
- Runs in the **user's own Python environment**, so the target script has access to all of the user's installed packages
- Minimal dependencies (ideally just `numpy` for array serialization)

### UX Flow

1. User downloads the PyProbe binary and runs it
2. User opens a Python script in the code viewer
3. User clicks variables to create probes
4. User clicks "Run" → the GUI binary launches the tracer:
   ```
   /path/to/user/python -m pyprobe_tracer --socket <host>:<port> script.py
   ```
5. The tracer connects to the GUI via socket, receives probe commands, sends captured data
6. If `pyprobe-tracer` is not installed, the GUI shows a helpful message: `pip install pyprobe-tracer`
7. Version handshake on connect: GUI checks that tracer protocol version is compatible

## Current Architecture — Key Files to Study

Before planning, read these files to understand the current implementation:

### Entry Point
- `pyprobe/__main__.py` — CLI entry point, calls `run_app()`

### GUI → Runner Spawning
- `pyprobe/gui/script_runner.py` — `ScriptRunner` class manages the subprocess lifecycle. Key method: `start()` creates `mp.Process(target=run_script_subprocess)` and sends probe commands via `mp.Queue`
- `pyprobe/gui/message_handler.py` — Polls the data queue for incoming messages from the runner, dispatches to GUI widgets

### Runner / Tracer Engine
- `pyprobe/core/runner.py` — `ScriptRunner` class (different from gui's), `run_script_subprocess()` entry point. Uses `exec(code, script_globals)` to run the target script
- `pyprobe/core/tracer.py` — `VariableTracer`, installs `sys.settrace` hooks
- `pyprobe/core/capture_manager.py` — Orchestrates ordered captures
- `pyprobe/core/anchor.py` — `ProbeAnchor` frozen dataclass (file:line:col:symbol)
- `pyprobe/core/data_classifier.py` — Auto-detects dtypes to select visualization

### IPC Layer
- `pyprobe/ipc/channels.py` — `IPCChannel` class wrapping `multiprocessing.Queue` + `shared_memory`
- `pyprobe/ipc/messages.py` — `Message` dataclass, `MessageType` enum, factory functions (`make_variable_data_msg`, `make_add_probe_cmd`, etc.)

### Analysis (stays in GUI)
- `pyprobe/analysis/ast_locator.py` — Maps cursor positions to variable names
- `pyprobe/analysis/anchor_mapper.py` — Maps AST positions to probe anchors

### Plugins (stay in GUI)
- `pyprobe/plugins/` — Visualization plugins (scalar, waveform, constellation, etc.)

## What Needs to Change

### IPC Rearchitecture
The `multiprocessing.Queue` and `shared_memory` IPC must be replaced with a cross-process mechanism that works between two independent Python interpreters. Options:
- **TCP sockets** with a JSON or msgpack protocol for commands/small data, and raw binary frames for numpy arrays
- **Unix domain sockets** (faster, but not available on Windows)
- **`multiprocessing.connection`** over TCP (built-in, supports pickling, works cross-process)
- **stdin/stdout pipes** via `subprocess.Popen` (simplest, but harder to do bidirectional)

Key constraint: large numpy arrays (e.g., 1M-sample waveforms) must transfer efficiently. The current shared memory approach is zero-copy. The new approach should minimize serialization overhead — consider `numpy.ndarray.tobytes()` + a length-prefixed binary protocol.

### Package Split
- `pyprobe/core/` and `pyprobe/ipc/` move (or are duplicated) into the `pyprobe-tracer` package
- The GUI keeps `pyprobe/gui/`, `pyprobe/analysis/`, `pyprobe/plugins/`, `pyprobe/plots/`
- Both sides share the message protocol definition (could be a shared sub-package or duplicated with version checking)

### Subprocess Launching
- `gui/script_runner.py` must change from `mp.Process(target=...)` to `subprocess.Popen([user_python, "-m", "pyprobe_tracer", ...])`
- Need a way to discover/configure the user's Python path (default: `python3` on PATH, configurable in GUI settings)
- The GUI must handle the tracer process lifecycle (start, monitor, terminate) via standard process management instead of multiprocessing

### Protocol Versioning
- The GUI and tracer must perform a version/protocol handshake on connect
- If incompatible, show a clear error: "Your pyprobe-tracer is v0.1, but this GUI requires v0.3. Run: pip install --upgrade pyprobe-tracer"

## Constraints

- **Do not break `python -m pyprobe script.py` dev mode.** The in-process/multiprocessing mode should still work for development. The socket-based mode is for standalone binary distribution.
- **TDD is mandatory.** No feature is considered functional unless it has explicit automated tests.
- **The UX constitution (`CONSTITUTION.md`) is non-negotiable.** Probing must remain a single gesture, no dialogs/forms.
- **Shared memory for large arrays is important for performance.** The rearchitected IPC should not make waveform rendering noticeably slower.

## Your Task

Create a detailed, milestone-based implementation plan for this rearchitecture. Each milestone should be:
1. **Small and independently testable** — can be merged and verified on its own
2. **Parallelizable where possible** — identify which milestones can proceed concurrently
3. **TDD-first** — specify what tests validate each milestone

The plan should cover:
1. New IPC protocol design (message format, handshake, array transfer)
2. `pyprobe-tracer` package structure and entry point
3. GUI-side subprocess launching and lifecycle management
4. Python interpreter discovery and configuration
5. Version compatibility checking
6. Migration path (keeping the old multiprocessing mode working during transition)
7. CI/CD updates (publish `pyprobe-tracer` to PyPI, update the binary build)

Save the plan to `plans/feb21/rearch_plan.md`.
