# Plan 6: Integration

**Focus:** Wire all components together in main_window.py.

**Branch:** `m1/integration`

**Dependencies:** Plans 0-5 (all others must be complete)

**Complexity:** Medium (M)

---

## Files to Modify

### `pyprobe/gui/main_window.py`

Replace watch list with code viewer, wire all signals.

**Key Changes:**

1. **New imports:**
```python
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.gui.code_viewer import CodeViewer
from pyprobe.gui.code_gutter import CodeGutter
from pyprobe.gui.code_highlighter import PythonHighlighter
from pyprobe.gui.file_watcher import FileWatcher
from pyprobe.gui.probe_registry import ProbeRegistry
from pyprobe.gui.probe_state import ProbeState
from pyprobe.analysis.anchor_mapper import AnchorMapper
from pyprobe.ipc.messages import MessageType, make_add_probe_cmd, make_remove_probe_cmd
```

2. **Layout changes in `_setup_ui()`:**
```python
# OLD: WatchListWidget (left) + ProbePanelContainer (right)
# NEW: CodeViewer+Gutter (left) + ProbePanelContainer (right)

splitter = QSplitter(Qt.Orientation.Horizontal)

# Code viewer with gutter
code_container = QWidget()
code_layout = QHBoxLayout(code_container)
code_layout.setContentsMargins(0, 0, 0, 0)
code_layout.setSpacing(0)

self._code_viewer = CodeViewer()
self._code_gutter = CodeGutter(self._code_viewer)
self._highlighter = PythonHighlighter(self._code_viewer.document())

code_layout.addWidget(self._code_gutter)
code_layout.addWidget(self._code_viewer)
splitter.addWidget(code_container)

# Probe panels (existing)
self._probe_container = ProbePanelContainer()
splitter.addWidget(self._probe_container)

splitter.setSizes([400, 800])
```

3. **New components:**
```python
self._file_watcher = FileWatcher(self)
self._probe_registry = ProbeRegistry(self)
self._probe_panels: Dict[ProbeAnchor, ProbePanel] = {}
```

4. **Signal connections in `_setup_signals()`:**
```python
# Code viewer signals
self._code_viewer.probe_requested.connect(self._on_probe_requested)
self._code_viewer.probe_removed.connect(self._on_probe_remove_requested)

# File watcher
self._file_watcher.file_changed.connect(self._on_file_changed)

# Probe registry
self._probe_registry.probe_state_changed.connect(self._on_probe_state_changed)
```

5. **New handler methods:**
- `_on_probe_requested(anchor)` - Handle click-to-probe
- `_on_probe_remove_requested(anchor)` - Handle probe removal
- `_complete_probe_removal(anchor)` - After animation
- `_on_file_changed(filepath)` - Handle file modification
- `_on_probe_state_changed(anchor, state)` - Handle state updates

6. **IPC message handling updates:**
```python
def _handle_message(self, msg: Message):
    if msg.msg_type == MessageType.DATA_PROBE_VALUE:
        anchor = ProbeAnchor.from_dict(msg.payload['anchor'])
        self._probe_registry.update_data_received(anchor)
        if anchor in self._probe_panels:
            self._probe_panels[anchor].update_data(...)
```

7. **Script loading updates:**
```python
def _on_run_script(self, script_path: str):
    self._code_viewer.load_file(script_path)
    self._file_watcher.watch_file(script_path)
    # ... existing run logic ...
```

---

## Data Flow

```
User clicks variable in CodeViewer
    ↓
probe_requested signal emitted with ProbeAnchor
    ↓
MainWindow._on_probe_requested(anchor):
    1. color = probe_registry.add_probe(anchor)
    2. code_viewer.set_probe_active(anchor, color)
    3. gutter.set_probed_line(anchor.line, color)
    4. panel = probe_container.create_panel(anchor, color)
    5. ipc.send_command(make_add_probe_cmd(anchor))
    ↓
Runner subprocess receives CMD_ADD_PROBE
    ↓
tracer.add_anchor_watch(anchor, config)
    ↓
Trace function matches (file, line, symbol)
    ↓
DATA_PROBE_VALUE sent back via IPC
    ↓
MainWindow._handle_message():
    1. probe_registry.update_data_received(anchor)
    2. probe_panels[anchor].update_data(value, dtype, shape)
```

---

## File Change Flow

```
User saves file in external editor
    ↓
QFileSystemWatcher detects change
    ↓
FileWatcher.file_changed signal
    ↓
MainWindow._on_file_changed(filepath):
    1. old_source = code_viewer.toPlainText()
    2. new_source = read from disk
    3. mapper = AnchorMapper(old_source, new_source, filepath)
    4. invalid = mapper.get_invalidated(active_anchors)
    5. For each invalid anchor:
        - code_viewer.set_probe_invalid(anchor)
        - probe_panels[anchor].set_state(INVALID)
    6. probe_registry.invalidate_anchors(invalid)
    7. code_viewer.reload_file()
    8. Re-apply valid probe highlights
```

---

## Verification

Run the M1 test script:

```bash
python -m pyprobe examples/dsp_demo.py
```

**Test Checklist:**

1. [ ] Code viewer displays with syntax highlighting
2. [ ] Hover over variable → subtle glow appears
3. [ ] Click variable → probe created
   - [ ] Variable background turns colored
   - [ ] Eye icon appears in gutter
   - [ ] Probe panel created on right
   - [ ] Identity label shows `symbol @ file:line`
   - [ ] State indicator shows pulsing yellow (ARMED)
4. [ ] Script runs → state indicator turns green (LIVE)
5. [ ] Click probed variable again → probe removed
   - [ ] Fade-out animation plays
   - [ ] Eye icon disappears
   - [ ] Panel removed
6. [ ] While running: click new variable → hot-probe works
7. [ ] Edit file externally, save → code reloads
8. [ ] Delete probed line → probe marked invalid (red X)

---

## Merge Conflict Risk

**High** - Modifies `main_window.py` which is central to the GUI.

**Mitigation:**
- Must run after all other plans merge
- Uses clear section markers (`# === M1 INTEGRATION ===`)
- Adds new methods rather than heavily modifying existing ones
- Layout changes are confined to `_setup_ui()` method
