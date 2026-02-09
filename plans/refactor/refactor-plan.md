# PyProbe Refactoring Plan

> **Living document** — Update after each refactoring session to maintain continuity.

---

## Overview

Goal: Reduce complexity in core files to improve AI agent comprehension, maintainability, and bug fix velocity.

| Metric | Before | Target | Current |
|--------|--------|--------|----------|
| `main_window.py` | 1062 lines | ~400 lines | 568 lines |
| `probe_panel.py` | 811 lines | ~400 lines (split) | 550 lines |
| `tracer.py` | 630 lines | ~400 lines | 630 lines |
| Duplicate code | `waveform_plot.py` + `waveform.py` | Delete duplicate | Pending |

---

## Progress Tracker

### ✅ Completed

| Task | Date | Details |
|------|------|---------|
| ScriptRunner extraction | 2026-02-09 | Moved 6 methods from `main_window.py` → `script_runner.py` (296 lines) |
| MessageHandler extraction | 2026-02-09 | Moved `_poll_ipc`, `_handle_message` → `message_handler.py` (174 lines) |
| ProbeController extraction | 2026-02-09 | Moved probe lifecycle, lens, and overlay logic → `probe_controller.py` (464 lines). Reduced `main_window.py` from 901 to 568 lines. |
| ProbePanelContainer extraction | 2026-02-09 | Moved `ProbePanelContainer` → `panel_container.py` (260 lines). Reduced `probe_panel.py` from 811 to 550 lines. |

### 🔄 In Progress

*None currently*

### 📋 Remaining Tasks

| Priority | Task | Effort | Impact | Dependencies |
|----------|------|--------|--------|--------------|
| 1 | Consolidate waveform duplication | 4h | Medium | None |
| 2 | Simplify `tracer.py` | 1 day | Medium | None |

---

## Detailed Task Specifications

### Task 1: Extract MessageHandler

**Goal**: Move IPC message polling and dispatch to dedicated class.

**File**: Create `pyprobe/gui/message_handler.py`

**Methods to extract from `main_window.py`**:
- `_poll_ipc()` → `poll()` (already uses ScriptRunner.ipc)
- `_handle_message()` → `dispatch()`
- `_on_variable_data()` → emit signal instead

**Interface**:
```python
class MessageHandler(QObject):
    variable_data = pyqtSignal(ProbeAnchor, object)
    probe_value = pyqtSignal(ProbeAnchor, dict)
    script_ended = pyqtSignal()
    exception_raised = pyqtSignal(dict)
    
    def __init__(self, script_runner: ScriptRunner): ...
    def start_polling(self, interval_ms: int = 16): ...
    def stop_polling(self): ...
```

**Verification**: All existing tests pass, manual test with `dsp_demo.py`.

---

### Task 2: Extract ProbeController

**Goal**: Move probe lifecycle management to dedicated class.

**File**: Create `pyprobe/gui/probe_controller.py`

**Methods to extract from `main_window.py`**:
- `_on_probe_requested()`
- `_on_probe_remove_requested()`
- `_complete_probe_removal()`
- `_on_lens_changed()`
- `_on_overlay_requested()`

**Interface**:
```python
class ProbeController(QObject):
    probe_added = pyqtSignal(ProbeAnchor, QColor)
    probe_removed = pyqtSignal(ProbeAnchor)
    
    def __init__(self, registry: ProbeRegistry, container: ProbePanelContainer): ...
    def add_probe(self, anchor: ProbeAnchor) -> bool: ...
    def remove_probe(self, anchor: ProbeAnchor): ...
    def update_data(self, anchor: ProbeAnchor, data: dict): ...
```

---

### Task 3: Split `probe_panel.py`

**Goal**: Separate `ProbePanelContainer` from `ProbePanel`.

**Files**:
- Keep `ProbePanel` in `probe_panel.py`
- Move `ProbePanelContainer` to `panel_container.py`

**Steps**:
1. Create `panel_container.py`
2. Move class with all methods
3. Update imports in `main_window.py`, tests

---

### Task 4: Consolidate Waveform Duplication

**Goal**: Migrate `plot_factory.py` to use plugin system, delete `waveform_plot.py`.

**Current state**:
- `pyprobe/plots/waveform_plot.py` (legacy, 640 lines)
- `pyprobe/plugins/waveform.py` (plugin version, 525 lines)
- `pyprobe/plots/plot_factory.py` imports `WaveformPlot`

**Steps**:
1. Update `plot_factory.py` to import from plugins
2. Verify all functionality works
3. Delete `waveform_plot.py`
4. Update any documentation references

---

### Task 5: Simplify `tracer.py`

**Goal**: Remove legacy trace path, extract deferred capture logic.

**Current issues**:
- Dual trace functions: `_trace_func` (legacy) and `_trace_func_anchored`
- Complex deferred capture mixed with trace logic

**Steps**:
1. Remove `_trace_func` completely (verify not called)
2. Extract `DeferredCaptureManager` class
3. Simplify remaining tracer

---

## References

### Key Files
- [main_window.py](file:///Users/ppal/repos/pyprobe/pyprobe/gui/main_window.py) (~900 lines after MessageHandler)
- [script_runner.py](file:///Users/ppal/repos/pyprobe/pyprobe/gui/script_runner.py) (296 lines) ✅
- [message_handler.py](file:///Users/ppal/repos/pyprobe/pyprobe/gui/message_handler.py) (174 lines) ✅
- [probe_panel.py](file:///Users/ppal/repos/pyprobe/pyprobe/gui/probe_panel.py) (811 lines)
- [tracer.py](file:///Users/ppal/repos/pyprobe/pyprobe/core/tracer.py) (630 lines)
- [waveform_plot.py](file:///Users/ppal/repos/pyprobe/pyprobe/plots/waveform_plot.py) (640 lines)
- [waveform.py](file:///Users/ppal/repos/pyprobe/pyprobe/plugins/waveform.py) (525 lines)

### Tests
Run after each change:
```bash
source .venv/bin/activate && python -m pytest tests/ -v
```

### Backlog
See [BACKLOG.md](file:///Users/ppal/repos/pyprobe/.agent/BACKLOG.md) P1.5 section for user-facing tracking.

---

## Session Log

### 2026-02-09 (Agent Session 1)
- Completed ScriptRunner extraction
- MainWindow reduced from 1062 → ~990 lines
- All 76 tests passing

### 2026-02-09 (Agent Session 2)
- Completed MessageHandler extraction
- MainWindow reduced from ~970 → 900 lines
- All 76 tests passing
