# CLAUDE.md

This file provides guidance for working with code in this repository.

## What is PyProbe

PyProbe is an interactive variable-probing debugger for Python DSP development. Users hover over variables in a code viewer, click to create probes, and see live visualizations (waveforms, constellations, scalar histories) update as the target script executes. The core philosophy is in CONSTITUTION.md — probing must be a single gesture, the tool must disappear, and code is always the source of truth.

## Commands

```bash
# create venv if it doesn't exist
uv venv --python 3.12

# Install dependencies (uses uv with pyproject.toml)
uv sync

# Run the application
./.venv/bin/python -m pyprobe [script.py] [--auto-run] [--auto-quit]
./.venv/bin/python -m pyprobe script.py -p "line:symbol:instance" -w "line:symbol"

# Run all test suites (core → ipc → gui → top-level)
./.venv/bin/python run_tests.py

# Run a single suite
./.venv/bin/python run_tests.py --suite core
./.venv/bin/python run_tests.py --suite gui
./.venv/bin/python run_tests.py --suite ipc
./.venv/bin/python run_tests.py --suite top-level

# Run a single test file
./.venv/bin/python -m pytest tests/core/test_tracer.py

# Run with extra pytest flags
./.venv/bin/python run_tests.py -v --failfast
```

## Architecture

PyProbe runs as two processes connected via IPC:

**GUI process** (PyQt6 + pyqtgraph) — code viewer, probe panels, plot rendering
**Runner subprocess** — executes the target script with `sys.settrace` hooks to capture probed variables

### Layer structure

- **`core/`** — Tracing engine. `tracer.py` installs sys.settrace hooks that intercept variable values at anchored locations. `runner.py` manages the subprocess lifecycle. `anchor.py` defines `ProbeAnchor` (frozen dataclass: file:line:col:symbol), the immutable identity of every probe. `capture_manager.py` orchestrates ordered captures. `data_classifier.py` auto-detects dtypes to select the right visualization.

- **`analysis/`** — AST-based code analysis. `ast_locator.py` maps cursor positions to variable names. `anchor_mapper.py` maps AST positions to probe anchors.

- **`ipc/`** — Inter-process communication. `messages.py` defines the message protocol (MessageType enum + payload dict). `channels.py` implements bidirectional IPC: queue-based for small messages (<10KB), shared memory for large numpy arrays.

- **`gui/`** — UI layer. `main_window.py` is the central window. `code_viewer.py` renders source with probe markers. `probe_controller.py` / `probe_registry.py` / `probe_panel.py` manage the probe lifecycle (Armed → Live → Removed). `plots/` contains the rendering engine. `theme/` has multiple themes (Anthropic, Cyberpunk, Monokai, Ocean, etc.) managed by `ThemeManager.instance()`.

- **`plugins/`** — Visualization plugin system. `base.py` defines `ProbePlugin` ABC. Built-in plugins: scalar, scalar_history (line chart), waveform (IQ), constellation (complex scatter), complex_plots (mag/phase). `PluginRegistry.instance()` handles registration and priority-based auto-selection.

### Data flow

1. User clicks a variable in the code viewer → `ASTLocator` identifies the symbol → `ProbeAnchor` created
2. GUI sends probe config to runner subprocess via IPC queue
3. Runner's `VariableTracer.trace_function()` fires on matching file+line, captures the value
4. `CaptureRecord` (with seq_num, timestamp) sent back: small values via queue, large arrays via shared memory
5. GUI `MessageHandler` receives data → updates `ProbePanel` → plugin renders the visualization

### Key patterns

- **Qt Signals/Slots** for thread-safe GUI updates (`variable_received`, `script_ended`, `exception_occurred`)
- **Frozen dataclasses** for immutable identities (`ProbeAnchor`), mutable dataclasses for runtime config
- **Singleton registries**: `ThemeManager.instance()`, `PluginRegistry.instance()`
- **Callbacks**: `on_*` prefix for event handlers, `make_*_cmd()`/`make_*_msg()` for message factories
- **Logging**: `get_logger(__name__)` pattern; debug log at `/tmp/pyprobe_debug.log`, state trace at `/tmp/pyprobe_state_trace.log`

## Testing

Tests use `pytest` with `pytest-qt` for GUI tests. Test suites are in `tests/core/`, `tests/ipc/`, `tests/gui/`, and top-level integration tests in `tests/`. The `conftest.py` provides shared fixtures. GUI tests require a display (or virtual framebuffer).

### ⚠️ Parallelism masks bugs

Running tests with `-p 4` distributes files across workers, reducing accumulated deferred Qt events per process. This hides order-dependent crashes that appear at `-p 1`. **A test that only passes because it's isolated is still broken.** The pre-push hook (`.git/hooks/pre-push`) enforces a sequential GUI test pass before pushing to main.

### ⚠️ Qt widget lifecycle in tests

> **RULE: If a test creates a `QWidget`, it MUST call `qtbot.addWidget(w)`. Always. No exceptions.**

**General principle:** When a Qt/pyqtgraph widget is created in a test and not explicitly destroyed, Python's garbage collector will destroy it at an unpredictable time — often during pytest teardown. At that point, Qt's event loop may still have **deferred events** (layout recalculations, paint events, size hint queries) queued against the widget's internal objects. Those internal objects get partially destroyed in an undefined order, so Qt fires a callback on a half-dead object and crashes.

This is invisible when it works, and baffling when it doesn't — the test assertions pass, but teardown explodes with inscrutable errors from deep inside pyqtgraph or Qt internals.

**When creating or modifying any QWidget in a test, guard against this:**

1. **In tests:** Always register widgets with `qtbot.addWidget(w)` **and** end with explicit cleanup. `qtbot.addWidget()` gives pytest-qt ownership of the C++ object's lifetime for deterministic cleanup; the manual teardown below is the belt-and-suspenders guarantee:
   ```python
   qtbot.addWidget(w)   # register for lifecycle management
   # ... test body ...
   w.close()
   w.deleteLater()
   qapp.processEvents()
   ```
2. **In widget code:** Be aware that any method that internally creates/recreates Qt graphics objects (axis labels, legends, ViewBoxes) is adding deferred-event surface area. The more internal objects a widget creates post-construction, the more likely GC teardown will hit a race condition.
3. **In code review:** If a new test creates a widget but has no cleanup or no `qtbot.addWidget()`, flag it. It may pass today and break tomorrow when someone adds a secondary axis or legend rebuild.
4. **Never remove the `_flush_qt_events` autouse fixture** in `tests/gui/conftest.py`. It processes pending Qt events (`qapp.processEvents()`) after every test, preventing deferred callbacks (`QTimer.singleShot(0, ...)`, `deleteLater()`) from accumulating across tests and firing on already-freed C++ objects. This fixture is the project-wide safety net for the class of bugs described here.
5. **The `_enforce_widget_cleanup` autouse fixture** will `pytest.fail()` if any test creates a `pyprobe.*` widget that is still visible after teardown. If a test fails with "Leaked N widget(s) without cleanup", add `qtbot.addWidget(w)` + `close()`/`deleteLater()`/`processEvents()` in fixture teardown.

#### Past example: `ComplexMAWidget` `_sizeHint` teardown crash

Three tests in `test_probe_color_change.py::TestComplexMAWidgetColor` passed assertions but failed in teardown with `AttributeError: 'LabelItem' object has no attribute '_sizeHint'`.

**Why only these 3?** `ComplexMAWidget` is used across many test files, but the other test files either (a) already had `deleteLater()` cleanup (e.g. `test_draw_mode_e2e.py`, `test_draw_mode.py`), or (b) never called methods that trigger internal `LabelItem` recreation. The color-change tests were unique because `set_series_color()` calls `setLabel('left', ...)`, which *recreates* pyqtgraph's `LabelItem` objects post-construction. Those recreated labels have cached `_sizeHint` dicts that become dangling references when GC runs during teardown.

**Fix:** Added `w.close()` + `w.deleteLater()` + `qapp.processEvents()` to the three tests.

## Key constraints

- Python ≥ 3.12, type hints throughout
- The UX constitution (CONSTITUTION.md) is non-negotiable — never add dialogs/forms for probe creation, never allow silent failures, hover must predict click exactly
- Target scripts always run in a subprocess, never in the GUI process
- IPC threshold: messages <10KB use queues, larger payloads use shared memory
