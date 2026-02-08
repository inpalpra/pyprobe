# Sub-Agent 05: DockBar (Park/Restore)

## Context

You are implementing the DockBar — a bottom bar where users can "park" graphs to get them out of the way while keeping them alive and updating.

## Goal

Create a DockBar widget that shows minimized representations of parked graphs with sparkline previews.

## Constraints

- Parked graphs continue receiving data updates (Constitution §3)
- Bottom bar shows: graph title + color key(s) + tiny sparkline (optional P1)
- Click/drag from bar restores to main area
- No confirmation dialogs
- Parked graphs retain all state (pins, overlays)

## Expected Outputs

### File: `pyprobe/gui/dock_bar.py`

```python
from typing import Dict, Optional
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QFrame, QLabel
from PyQt6.QtCore import pyqtSignal, Qt

class DockBarItem(QFrame):
    """Single item in the dock bar representing a parked graph.
    
    Shows: [color_dot] [title]
    Click to restore to grid.
    """
    
    restore_requested = pyqtSignal()
    
    def __init__(self, title: str, color, parent: QWidget = None):
        ...
    
    def update_sparkline(self, data) -> None:
        """Update the mini sparkline preview."""
        ...
    
    def mousePressEvent(self, event) -> None:
        """Emit restore_requested on click."""
        ...

class DockBar(QWidget):
    """Bottom bar for parked graphs.
    
    Horizontal layout with scrollable overflow.
    """
    
    panel_restore_requested = pyqtSignal(str)  # anchor_key
    
    def __init__(self, parent: QWidget = None):
        ...
    
    def add_panel(self, anchor_key: str, title: str, color) -> None:
        """Add a parked panel representation."""
        ...
    
    def remove_panel(self, anchor_key: str) -> None:
        """Remove panel from dock bar (either restored or deleted)."""
        ...
    
    def update_data(self, anchor_key: str, data) -> None:
        """Update sparkline for a parked panel."""
        ...
    
    def is_empty(self) -> bool:
        """Check if dock bar has no items (can hide)."""
        ...
```

### Modifications to `MainWindow`

Add DockBar to layout:

```python
def _setup_ui(self):
    ...
    # Add dock bar at bottom
    self._dock_bar = DockBar(self)
    self._dock_bar.setVisible(False)  # Hidden when empty
    main_layout.addWidget(self._dock_bar)
```

### Modifications to `ProbePanel`

Add park action:

```python
def contextMenuEvent(self, event):
    menu = QMenu(self)
    ...
    park_action = menu.addAction("Park to Bar")
    park_action.triggered.connect(lambda: self.park_requested.emit())
```

## State Machine

```
ACTIVE (visible in grid) ────> PARKED (bottom bar, still updating)
                        park

PARKED ──────────────────────> ACTIVE
                        restore
```

## Data Flow for Parked Panels

```
IPC message arrives
    ↓
MainWindow._on_variable_data()
    ↓
Check if panel is parked
    ↓
If parked: DockBar.update_data(anchor_key, data)
If active: ProbePanel.update_data(...)
```

## Integration Points

1. `MainWindow._setup_ui()` — add DockBar widget
2. `ProbePanel` — add `park_requested` signal
3. `ProbePanelContainer` — handle park/restore transitions
4. Data flow — route updates to parked panels

## Test Plan

1. Unit test: `test_dock_bar.py`
   - Create DockBar, add item
   - Verify item visible
   - Simulate click → verify restore_requested signal
   - Remove item → verify is_empty()

2. Manual test:
   - Probe a variable
   - Right-click → "Park to Bar"
   - Verify panel moves to bottom bar
   - Verify bar shows title and color
   - Run script → verify parked panel updates
   - Click on bar item → verify restores to grid

## Success Criteria

- [ ] Park action moves panel to bottom bar
- [ ] Bar shows title + color dot
- [ ] Parked panels continue updating
- [ ] Click on bar item restores to grid
- [ ] Bar auto-hides when empty
