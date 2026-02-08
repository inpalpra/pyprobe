# Sub-Agent 01: Axis Controller and Pinning

## Context

You are implementing the axis pinning system for PyProbe Graph Palette. This is the foundation for all axis control features.

## Goal

Create an AxisController class that manages pin state for X and Y axes, with visual indicators (lock icons).

## Constraints

- Uses PyQtGraph `PlotItem` and `ViewBox`
- Constitution §2: Every state change must have visible feedback
- Constitution §11: Controls must be discoverable

## Inputs

- `PlotItem` from PyQtGraph (the chart widget)
- User interactions: zoom, pan, manual range edit

## Expected Outputs

### File: `pyprobe/plots/axis_controller.py`

```python
from enum import Enum, auto
from typing import Optional
from pyqtgraph import PlotItem

class AxisPinState(Enum):
    AUTO = auto()   # Autoscale on every update
    PINNED = auto() # Frozen range

class AxisController:
    """Manages axis pin state for a PlotItem."""
    
    def __init__(self, plot_item: PlotItem):
        ...
    
    def is_pinned(self, axis: str) -> bool:
        """Check if axis ('x' or 'y') is pinned."""
        ...
    
    def set_pinned(self, axis: str, pinned: bool) -> None:
        """Set pin state for axis. Updates PlotItem autoscale."""
        ...
    
    def toggle_pin(self, axis: str) -> None:
        """Toggle pin state for axis."""
        ...
    
    def reset(self) -> None:
        """Unpin both axes and trigger autoscale."""
        ...
    
    @property
    def x_pinned(self) -> bool: ...
    
    @property
    def y_pinned(self) -> bool: ...
```

### File: `pyprobe/plots/pin_indicator.py`

```python
from PyQt6.QtWidgets import QLabel, QWidget
from PyQt6.QtCore import Qt

class PinIndicator(QWidget):
    """Lock icon overlay showing axis pin state.
    
    Positioned inside the plot area, near the axis.
    Shows 🔒X and/or 🔒Y when axes are pinned.
    """
    
    def __init__(self, parent: QWidget):
        ...
    
    def set_x_pinned(self, pinned: bool) -> None:
        """Show/hide X-axis lock indicator."""
        ...
    
    def set_y_pinned(self, pinned: bool) -> None:
        """Show/hide Y-axis lock indicator."""
        ...
```

## Integration Points

1. `WaveformPlot._configure_plot()` — instantiate AxisController
2. `WaveformPlot.update_data()` — check pin state before autoscale
3. `ViewBox.sigRangeChangedManually` — trigger pin on user interaction

## Test Plan

1. Unit test: `test_axis_controller.py`
   - Create AxisController with mock PlotItem
   - Verify initial state is AUTO for both axes
   - Verify `set_pinned()` updates state
   - Verify `reset()` returns to AUTO

2. Manual test:
   - Probe a variable, zoom with mouse
   - Verify 🔒X or 🔒Y appears
   - Press `R` key
   - Verify lock icons disappear and autoscale resumes

## Success Criteria

- [ ] Zooming/panning auto-pins affected axis
- [ ] Lock icon visible when pinned
- [ ] Reset key unpins and autoscales
- [ ] Pin state survives data updates
