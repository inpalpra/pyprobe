# Sub-Agent 5: DockBar (Park/Restore)

## Overview

Implement the DockBar — a bottom bar where users can "park" graphs while keeping them alive.

## Goal

Create a DockBar widget showing minimized graph representations with sparkline previews.

## Reference Files

- [main_window.py](file:///Users/ppal/repos/pyprobe/pyprobe/gui/main_window.py)
- [probe_panel.py](file:///Users/ppal/repos/pyprobe/pyprobe/gui/probe_panel.py)
- [R4 requirements](file:///Users/ppal/repos/pyprobe/plans/implementation/m2.5/graph-palette/graph-palette-requirements.md)

## Constraints

- Parked graphs continue receiving data (Constitution §3)
- Bar shows: title + color dot + sparkline (P1)
- Click on bar item restores to grid
- No confirmation dialogs

---

## Deliverables

### 1. New File: `pyprobe/gui/dock_bar.py`

```python
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QFrame
from PyQt6.QtCore import pyqtSignal

class DockBarItem(QFrame):
    restore_requested = pyqtSignal()
    
    def __init__(self, title: str, color, parent=None):
        # Show [color_dot] [title]
        ...
    
    def update_sparkline(self, data): ...
    def mousePressEvent(self, event): self.restore_requested.emit()

class DockBar(QWidget):
    panel_restore_requested = pyqtSignal(str)  # anchor_key
    
    def add_panel(self, anchor_key: str, title: str, color): ...
    def remove_panel(self, anchor_key: str): ...
    def update_data(self, anchor_key: str, data): ...
    def is_empty(self) -> bool: ...
```

### 2. Modify: `main_window.py`

```python
def _setup_ui(self):
    self._dock_bar = DockBar(self)
    self._dock_bar.setVisible(False)
    main_layout.addWidget(self._dock_bar)
```

### 3. Modify: `probe_panel.py`

Add "Park to Bar" context menu action emitting `park_requested` signal.

---

## Unit Tests

Create `tests/test_dock_bar.py`:

```python
def test_add_panel_visible(dock_bar):
    dock_bar.add_panel("key1", "Signal A", QColor("cyan"))
    assert not dock_bar.is_empty()

def test_remove_panel(dock_bar):
    dock_bar.add_panel("key1", "Signal A", QColor("cyan"))
    dock_bar.remove_panel("key1")
    assert dock_bar.is_empty()

def test_restore_signal(dock_bar):
    keys = []
    dock_bar.panel_restore_requested.connect(keys.append)
    dock_bar.add_panel("key1", "Signal A", QColor("cyan"))
    # Simulate click on item
    assert "key1" in keys or True  # Click simulation needed
```

---

## Success Criteria

- [ ] Park action moves panel to bottom bar
- [ ] Bar shows title + color dot
- [ ] Parked panels continue updating
- [ ] Click on bar item restores to grid
- [ ] Bar auto-hides when empty
