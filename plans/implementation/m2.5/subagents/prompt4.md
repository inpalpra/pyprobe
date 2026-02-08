# Sub-Agent 4: Maximize/Restore

## Overview

Implement double-click to maximize and double-click again to restore for PyProbe graphs.

## Goal

Allow users to double-click a plot background to expand it, hiding other plots but keeping them alive.

## Reference Files

- [probe_panel.py](file:///Users/ppal/repos/pyprobe/pyprobe/gui/probe_panel.py)
- [main_window.py](file:///Users/ppal/repos/pyprobe/pyprobe/gui/main_window.py)
- [R3 requirements](file:///Users/ppal/repos/pyprobe/plans/implementation/m2.5/graph-palette/graph-palette-requirements.md)

## Constraints

- Double-click on background only (NOT axes, tick labels, traces)
- Animation: 150-200ms transition
- Hidden panels remain alive and updating

---

## Hit-Test Priority (Critical)

| Priority | Target | Action |
|----------|--------|--------|
| 1 (Highest) | Axis tick label | In-place edit |
| 2 | Axis line | Ignored |
| 3 | Data traces | Ignored |
| 4 (Lowest) | Empty background | Toggle maximize |

---

## Deliverables

### 1. New File: `pyprobe/gui/layout_manager.py`

```python
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

class LayoutManager:
    def __init__(self, container: QWidget):
        self._container = container
        self._maximized_panel = None
        self._original_geometries = {}
    
    def toggle_maximize(self, panel: QWidget) -> None:
        # If panel maximized -> restore
        # If other maximized -> restore that, maximize this
        # If none maximized -> maximize this
        ...
    
    def restore(self) -> None: # Restore grid layout
    def is_maximized(self) -> bool: ...
```

### 2. Modify: `probe_panel.py`

```python
# Add signal:
maximize_requested = pyqtSignal()

def mouseDoubleClickEvent(self, event):
    if self._is_on_axis(event.pos()): return
    if self._is_on_trace(event.pos()): return
    self.maximize_requested.emit()
```

### 3. Modify: `ProbePanelContainer`

```python
def __init__(self, ...):
    self._layout_manager = LayoutManager(self)

def _on_panel_maximize_requested(self, panel):
    self._layout_manager.toggle_maximize(panel)
```

---

## Unit Tests

Create `tests/test_layout_manager.py`:

```python
def test_initial_no_maximize(manager):
    assert not manager.is_maximized()

def test_toggle_maximizes(manager, panel):
    manager.toggle_maximize(panel)
    assert manager.maximized_panel == panel

def test_toggle_twice_restores(manager, panel):
    manager.toggle_maximize(panel)
    manager.toggle_maximize(panel)
    assert not manager.is_maximized()

def test_maximize_another_restores_first(manager, panel1, panel2):
    manager.toggle_maximize(panel1)
    manager.toggle_maximize(panel2)
    assert manager.maximized_panel == panel2
```

---

## Success Criteria

- [ ] Double-click background → maximize
- [ ] Double-click again → restore
- [ ] Clicking axes/traces does NOT maximize
- [ ] Animation 150-200ms
- [ ] Hidden panels continue updating
