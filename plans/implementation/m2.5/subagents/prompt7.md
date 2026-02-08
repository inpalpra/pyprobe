# Sub-Agent 7: Keyboard Shortcuts and Focus Model

## Overview

Implement keyboard shortcuts and click-to-focus model for graph interactions.

## Goal

Enable keyboard-driven control with clear visual feedback on focused plots.

## Reference Files

- [probe_panel.py](file:///Users/ppal/repos/pyprobe/pyprobe/gui/probe_panel.py)
- [axis_controller.py](file:///Users/ppal/repos/pyprobe/pyprobe/plots/axis_controller.py)
- [R7 requirements](file:///Users/ppal/repos/pyprobe/plans/implementation/m2.5/graph-palette/graph-palette-requirements.md)

## Focus Model

- Click anywhere on plot → keyboard focus
- Only one plot can have focus
- Hover does NOT transfer focus
- Focused plot shows cyan border glow

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `X` | Toggle X-axis pin |
| `Y` | Toggle Y-axis pin |
| `R` | Reset (unpin + autoscale) |
| `Escape` | Return to Pointer mode |
| `Tab` | Cycle to next plot |

---

## Deliverables

### 1. New File: `pyprobe/gui/focus_manager.py`

```python
from PyQt6.QtCore import QObject, pyqtSignal

class FocusManager(QObject):
    focus_changed = pyqtSignal(object)
    
    def __init__(self, container):
        self._panels = []
        self._focused = None
    
    def set_focus(self, panel): ...
    def clear_focus(self): ...
    def focus_next(self): ...
```

### 2. Modify: `probe_panel.py`

```python
self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

def focusInEvent(self, event):
    self._show_focus_indicator(True)

def focusOutEvent(self, event):
    self._show_focus_indicator(False)

def keyPressEvent(self, event):
    if event.key() == Qt.Key.Key_X:
        self._axis_controller.toggle_pin('x')
    elif event.key() == Qt.Key.Key_Y:
        self._axis_controller.toggle_pin('y')
    elif event.key() == Qt.Key.Key_R:
        self._axis_controller.reset()
    elif event.key() == Qt.Key.Key_Escape:
        self._toolbar.set_mode(InteractionMode.POINTER)
```

### 3. Modify: `ProbePanelContainer`

Handle Tab navigation via FocusManager.

---

## Unit Tests

Create `tests/test_focus_manager.py`:

```python
def test_set_focus(focus_manager, panel):
    focus_manager.set_focus(panel)
    assert focus_manager.focused_panel == panel

def test_focus_next_cycles(focus_manager, panel1, panel2):
    focus_manager.set_focus(panel1)
    focus_manager.focus_next()
    assert focus_manager.focused_panel == panel2

def test_clear_focus(focus_manager, panel):
    focus_manager.set_focus(panel)
    focus_manager.clear_focus()
    assert focus_manager.focused_panel is None
```

---

## Success Criteria

- [ ] Click on plot gives keyboard focus
- [ ] Focused plot shows cyan glow
- [ ] X/Y/R/Escape keys work
- [ ] Tab cycles through plots
- [ ] Only one focused at a time
