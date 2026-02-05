# Plan 2: Code Viewer Widget

**Focus:** QPlainTextEdit with mouse tracking, hover highlighting, click-to-probe.

**Branch:** `m1/code-viewer`

**Dependencies:** Plan 0 (ProbeAnchor), Plan 1 (ASTLocator)

**Complexity:** Large (L)

**UX Requirements Addressed:**
- Cursor Trust (brutal teardown #4): Exact hover = exact click
- Gutter with eye icons (requirement #6)
- Scrollbar markers for probe locations (brutal teardown #7)

---

## Files to Create

### `pyprobe/gui/code_viewer.py`

Full code viewer widget with mouse tracking and click-to-probe functionality.

**Key features:**
- `setMouseTracking(True)` for hover detection
- `cursorForPosition(pos)` to get text position from mouse
- Signals: `probe_requested`, `probe_removed`, `hover_changed`
- Custom `paintEvent` for probe highlights
- `load_file()` / `reload_file()` methods

**Implementation:** See main plan file for full code (~240 lines).

### `pyprobe/gui/code_gutter.py`

Gutter widget showing line numbers and probe eye icons.

**Key features:**
- Synced scrolling with code viewer
- Eye icon (👁) drawing for probed lines
- Color-matched to probe color
- Auto-width based on line count

**Implementation:** See main plan file for full code (~100 lines).

### `pyprobe/gui/code_highlighter.py`

Python syntax highlighter with cyberpunk theme colors.

**Key features:**
- Keywords: Magenta
- Built-ins: Cyan
- Strings: Green
- Numbers: Yellow
- Comments: Gray italic
- Decorators: Orange

**Implementation:** See main plan file for full code (~120 lines).

---

## Key Implementation Notes

### Mouse Tracking Flow

```
mouseMoveEvent(event)
    ↓
cursorForPosition(event.pos()) → get (line, col)
    ↓
ast_locator.get_nearest_variable(line, col) → VariableLocation
    ↓
Create ProbeAnchor if found
    ↓
hover_changed.emit(anchor)
    ↓
viewport().update() → trigger paintEvent
```

### Click Toggle Logic

```python
def mousePressEvent(self, event):
    if self._hover_anchor in self._active_probes:
        self.probe_removed.emit(self._hover_anchor)
    else:
        self.probe_requested.emit(self._hover_anchor)
```

### Highlight Drawing

```python
def _draw_variable_highlight(painter, var, color, is_hover):
    # Calculate rectangle from (line, col_start, col_end)
    # Hover: subtle border
    # Active: filled background with alpha
```

---

## Verification

```bash
# Manual test: Load code viewer and interact
python -c "
from PyQt6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
from pyprobe.gui.code_viewer import CodeViewer
viewer = CodeViewer()
viewer.load_file('examples/dsp_demo.py')
viewer.show()
app.exec()
"
```

Expected behavior:
1. Code displays with syntax highlighting
2. Hover over variable → subtle highlight appears
3. Click variable → probe_requested signal emitted
4. Variable highlight turns colored (when set_probe_active called)

---

## Merge Conflict Risk

**None** - All new files.
