# Sub-Agent 3: Plot Toolbar (Translucent Hover Buttons)

## Overview

Create a translucent toolbar with 6 buttons that appears when users hover over a plot.

## Goal

Create `PlotToolbar` widget with Pointer, Pan, Zoom, Zoom-X, Zoom-Y, Reset buttons.

## Reference Files

- [probe_panel.py](file:///Users/ppal/repos/pyprobe/pyprobe/gui/probe_panel.py)
- [waveform_plot.py](file:///Users/ppal/repos/pyprobe/pyprobe/plots/waveform_plot.py)
- [axis_controller.py](file:///Users/ppal/repos/pyprobe/pyprobe/plots/axis_controller.py)
- [R6 requirements](file:///Users/ppal/repos/pyprobe/plans/implementation/m2.5/graph-palette/graph-palette-requirements.md)

## Constraints

- Hidden by default, appears on plot hover
- Max opacity 40%
- Pointer is default mode
- Pan/Zoom modes revert to Pointer after action

---

## Deliverables

### 1. Create: `pyprobe/gui/icons/` with SVG icons

Files: `icon_pointer.svg`, `icon_pan.svg`, `icon_zoom.svg`, `icon_zoom_x.svg`, `icon_zoom_y.svg`, `icon_reset.svg`

### 2. New File: `pyprobe/gui/plot_toolbar.py`

```python
from enum import Enum, auto
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QButtonGroup
from PyQt6.QtCore import pyqtSignal, Qt, QPropertyAnimation

class InteractionMode(Enum):
    POINTER = auto()
    PAN = auto()
    ZOOM = auto()
    ZOOM_X = auto()
    ZOOM_Y = auto()

class PlotToolbar(QWidget):
    mode_changed = pyqtSignal(object)
    reset_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        # Create 5 mode buttons + 1 reset button
        # Position at top-right, fade in/out on hover
        ...
    
    def show_on_hover(self): # Fade to 40% opacity
    def hide_on_leave(self): # Fade to 0%
    def revert_to_pointer(self): # Called after pan/zoom action
```

### 3. Modify: `probe_panel.py`

- Add PlotToolbar as overlay child
- Connect `enterEvent` → `toolbar.show_on_hover()`
- Connect `leaveEvent` → `toolbar.hide_on_leave()`
- Connect signals to plot interaction modes

### 4. Modify: `waveform_plot.py`

Add `set_interaction_mode(mode)` method to configure ViewBox behavior.

---

## Unit Tests

Create `tests/test_plot_toolbar.py`:

```python
def test_default_mode_is_pointer(toolbar):
    assert toolbar.current_mode == InteractionMode.POINTER

def test_mode_changed_signal(toolbar):
    received = []
    toolbar.mode_changed.connect(received.append)
    toolbar._on_mode_clicked(InteractionMode.ZOOM)
    assert InteractionMode.ZOOM in received

def test_reset_signal(toolbar):
    called = []
    toolbar.reset_requested.connect(lambda: called.append(True))
    toolbar._reset_btn.click()
    assert len(called) == 1

def test_revert_to_pointer(toolbar):
    toolbar.set_mode(InteractionMode.ZOOM)
    toolbar.revert_to_pointer()
    assert toolbar.current_mode == InteractionMode.POINTER
```

---

## Success Criteria

- [ ] Toolbar appears on hover with ≤40% opacity
- [ ] All 6 buttons functional
- [ ] Pan/Zoom modes revert to Pointer after action
- [ ] Reset triggers AxisController.reset()
- [ ] All unit tests pass
