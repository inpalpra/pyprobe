# Sub-Agent 03: Plot Toolbar (Translucent Hover Buttons)

## Context

You are implementing the translucent toolbar that appears when users hover over a plot. This provides discoverable access to pan, zoom, and reset controls.

## Goal

Create a PlotToolbar widget with 6 buttons (Pointer, Pan, Zoom, Zoom-X, Zoom-Y, Reset) that appears on hover and fades when not needed.

## Constraints

- Hidden by default, appears on plot hover
- Max opacity 40% when visible (Constitution §12)
- Never obscures data traces
- Pointer mode is default
- Pan/Zoom modes revert to Pointer after action

## Expected Outputs

### File: `pyprobe/gui/plot_toolbar.py`

```python
from enum import Enum, auto
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt

class InteractionMode(Enum):
    POINTER = auto()  # Default, click-through
    PAN = auto()       # Drag to pan
    ZOOM = auto()      # Drag rectangle, zoom both
    ZOOM_X = auto()    # Horizontal zoom only
    ZOOM_Y = auto()    # Vertical zoom only

class PlotToolbar(QWidget):
    """Translucent overlay toolbar for plot interaction modes.
    
    Appears on hover, fades when mouse leaves.
    Positioned at top-right of plot area.
    """
    
    # Signals
    mode_changed = pyqtSignal(InteractionMode)
    reset_requested = pyqtSignal()
    
    def __init__(self, parent: QWidget = None):
        ...
    
    def set_mode(self, mode: InteractionMode) -> None:
        """Set active interaction mode, update button states."""
        ...
    
    def show_on_hover(self) -> None:
        """Fade in the toolbar."""
        ...
    
    def hide_on_leave(self) -> None:
        """Fade out the toolbar."""
        ...
    
    @property
    def current_mode(self) -> InteractionMode:
        ...
```

### Icon Requirements

Use custom SVG icons matching PyProbe's dark cyberpunk aesthetic:

| Button | Icon Description |
|--------|------------------|
| Pointer | Cursor arrow (minimal) |
| Pan | Open hand |
| Zoom | Magnifier with +/- |
| Zoom-X | Horizontal double-arrow |
| Zoom-Y | Vertical double-arrow |
| Reset | Circular refresh arrow |

Store in: `pyprobe/gui/icons/` as `.svg` files.

## Animation

```python
def show_on_hover(self):
    self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
    self.fade_animation.setDuration(150)
    self.fade_animation.setStartValue(0.0)
    self.fade_animation.setEndValue(0.4)
    self.fade_animation.start()
```

## Integration Points

1. `ProbePanel` — add PlotToolbar as overlay child
2. `ProbePanel.enterEvent()` — call `toolbar.show_on_hover()`
3. `ProbePanel.leaveEvent()` — call `toolbar.hide_on_leave()`
4. Connect `mode_changed` → `WaveformPlot._set_interaction_mode()`
5. Connect `reset_requested` → `AxisController.reset()`

## Test Plan

1. Unit test: `test_plot_toolbar.py`
   - Verify initial mode is POINTER
   - Verify mode_changed signal on button click
   - Verify reset_requested signal on Reset click

2. Manual test:
   - Hover over plot → toolbar appears (semi-transparent)
   - Click Pan → cursor changes to hand
   - Drag on plot → axes pan
   - Release → mode reverts to Pointer
   - Click Reset → axes autoscale

## Success Criteria

- [ ] Toolbar hidden when mouse not over plot
- [ ] Toolbar ≤40% opacity when visible
- [ ] Pan/Zoom modes work correctly
- [ ] Modes revert to Pointer after action
- [ ] Escape key returns to Pointer mode
- [ ] Toolbar does not obscure data traces
