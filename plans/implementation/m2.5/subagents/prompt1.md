# Sub-Agent 1: Axis Controller and Pinning

## Overview

You are implementing the axis pinning system for PyProbe Graph Palette. This is the **foundation** for all axis control features — every other graph interaction depends on this working correctly.

## Goal

Create an `AxisController` class that manages pin state for X and Y axes, with visual indicators (lock icons).

## Constitution Compliance

| § | Principle | How This Task Complies |
|---|-----------|------------------------|
| 2 | Acknowledge Every Action | Lock icon appears/disappears on state change |
| 6 | Obvious Lifecycle | PINNED vs AUTO is visually distinct |
| 11 | Discovery > Docs | Lock icons are visible without reading documentation |

## Constraints

- Uses PyQtGraph `PlotItem` and `ViewBox`
- No external dependencies beyond PyQt6/PyQtGraph
- Pin state must survive data updates

---

## Reference Files

Before starting, read these files to understand the existing architecture:

| File | Purpose |
|------|---------|
| [waveform_plot.py](file:///Users/ppal/repos/pyprobe/pyprobe/plots/waveform_plot.py) | Primary plot widget to integrate with |
| [base_plot.py](file:///Users/ppal/repos/pyprobe/pyprobe/plots/base_plot.py) | Base class (deprecated, but shows pattern) |
| [probe_panel.py](file:///Users/ppal/repos/pyprobe/pyprobe/gui/probe_panel.py) | Container that holds plots |
| [graph-palette-requirements.md](file:///Users/ppal/repos/pyprobe/plans/implementation/m2.5/graph-palette/graph-palette-requirements.md) | R1: Axis Pinning requirements |

---

## Deliverables

### 1. New File: `pyprobe/plots/axis_controller.py`

```python
"""
Axis pin state controller for PyQtGraph plots.

Manages AUTO/PINNED state for X and Y axes.
"""

from enum import Enum, auto
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
import pyqtgraph as pg


class AxisPinState(Enum):
    """Pin state for a single axis."""
    AUTO = auto()   # Autoscale on every update (default)
    PINNED = auto() # Frozen range, no autoscale


class AxisController(QObject):
    """Manages axis pin state for a PlotItem.
    
    Usage:
        controller = AxisController(plot_item)
        controller.set_pinned('x', True)  # Pin X axis
        if controller.x_pinned:
            # Skip autoscale for X
    
    Signals:
        pin_state_changed(axis: str, is_pinned: bool)
    """
    
    pin_state_changed = pyqtSignal(str, bool)  # axis, is_pinned
    
    def __init__(self, plot_item: pg.PlotItem):
        super().__init__()
        self._plot_item = plot_item
        self._x_state = AxisPinState.AUTO
        self._y_state = AxisPinState.AUTO
        
        # Connect to ViewBox range changes
        self._setup_signals()
    
    def _setup_signals(self) -> None:
        """Connect to ViewBox signals to detect manual range changes."""
        view_box = self._plot_item.getViewBox()
        # sigRangeChangedManually is emitted when user drags/zooms
        view_box.sigRangeChangedManually.connect(self._on_manual_range_change)
    
    def _on_manual_range_change(self, mask: list) -> None:
        """Handle manual range change (zoom/pan).
        
        Args:
            mask: [x_changed, y_changed] booleans
        """
        if mask[0]:  # X axis changed
            self.set_pinned('x', True)
        if mask[1]:  # Y axis changed
            self.set_pinned('y', True)
    
    def is_pinned(self, axis: str) -> bool:
        """Check if axis is pinned.
        
        Args:
            axis: 'x' or 'y'
        
        Returns:
            True if axis is pinned (no autoscale)
        """
        if axis == 'x':
            return self._x_state == AxisPinState.PINNED
        elif axis == 'y':
            return self._y_state == AxisPinState.PINNED
        raise ValueError(f"Invalid axis: {axis}")
    
    def set_pinned(self, axis: str, pinned: bool) -> None:
        """Set pin state for axis.
        
        Args:
            axis: 'x' or 'y'
            pinned: True to pin (disable autoscale)
        """
        new_state = AxisPinState.PINNED if pinned else AxisPinState.AUTO
        
        if axis == 'x':
            if self._x_state != new_state:
                self._x_state = new_state
                self._plot_item.enableAutoRange(x=not pinned)
                self.pin_state_changed.emit('x', pinned)
        elif axis == 'y':
            if self._y_state != new_state:
                self._y_state = new_state
                self._plot_item.enableAutoRange(y=not pinned)
                self.pin_state_changed.emit('y', pinned)
        else:
            raise ValueError(f"Invalid axis: {axis}")
    
    def toggle_pin(self, axis: str) -> None:
        """Toggle pin state for axis."""
        self.set_pinned(axis, not self.is_pinned(axis))
    
    def reset(self) -> None:
        """Unpin both axes and trigger autoscale."""
        self.set_pinned('x', False)
        self.set_pinned('y', False)
        # Force immediate autoscale
        self._plot_item.autoRange()
    
    @property
    def x_pinned(self) -> bool:
        """Read-only: is X axis pinned."""
        return self._x_state == AxisPinState.PINNED
    
    @property
    def y_pinned(self) -> bool:
        """Read-only: is Y axis pinned."""
        return self._y_state == AxisPinState.PINNED
```

### 2. New File: `pyprobe/plots/pin_indicator.py`

```python
"""
Lock icon indicator for pinned axes.

Positioned inside the plot area, near the axis labels.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class PinIndicator(QWidget):
    """Lock icon overlay showing axis pin state.
    
    Shows 🔒X and/or 🔒Y when axes are pinned.
    Positioned at top-left of plot area.
    """
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._setup_ui()
        self._x_pinned = False
        self._y_pinned = False
    
    def _setup_ui(self) -> None:
        """Create the indicator UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        
        # Lock icons
        self._x_label = QLabel("🔒X")
        self._y_label = QLabel("🔒Y")
        
        # Style
        font = QFont()
        font.setPointSize(10)
        
        style = """
            QLabel {
                color: #00ffff;
                background-color: rgba(0, 0, 0, 0.5);
                padding: 2px 4px;
                border-radius: 3px;
            }
        """
        
        for label in [self._x_label, self._y_label]:
            label.setFont(font)
            label.setStyleSheet(style)
            label.hide()
            layout.addWidget(label)
        
        layout.addStretch()
        
        # Position at top-left
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    
    def set_x_pinned(self, pinned: bool) -> None:
        """Show/hide X-axis lock indicator."""
        self._x_pinned = pinned
        self._x_label.setVisible(pinned)
    
    def set_y_pinned(self, pinned: bool) -> None:
        """Show/hide Y-axis lock indicator."""
        self._y_pinned = pinned
        self._y_label.setVisible(pinned)
    
    def update_from_controller(self, controller) -> None:
        """Update indicators from AxisController state."""
        self.set_x_pinned(controller.x_pinned)
        self.set_y_pinned(controller.y_pinned)
```

### 3. Modify: `pyprobe/plots/waveform_plot.py`

Add these modifications:

```python
# At top of file, add imports:
from .axis_controller import AxisController
from .pin_indicator import PinIndicator

# In __init__(), after _setup_ui():
self._axis_controller = AxisController(self._plot_item)
self._pin_indicator = PinIndicator(self)
self._axis_controller.pin_state_changed.connect(self._on_pin_state_changed)

# Add method:
def _on_pin_state_changed(self, axis: str, is_pinned: bool) -> None:
    """Update pin indicator when axis state changes."""
    if axis == 'x':
        self._pin_indicator.set_x_pinned(is_pinned)
    else:
        self._pin_indicator.set_y_pinned(is_pinned)

# Modify update_data() to respect pin state:
# Before any autoRange() call, check:
if not self._axis_controller.x_pinned:
    # Only autoscale X if not pinned
    ...
if not self._axis_controller.y_pinned:
    # Only autoscale Y if not pinned
    ...

# Add public accessor:
@property
def axis_controller(self) -> AxisController:
    """Access the axis controller for external control."""
    return self._axis_controller
```

---

## Unit Tests

Create file: `tests/test_axis_controller.py`

```python
"""Unit tests for AxisController."""

import pytest
from unittest.mock import MagicMock, patch
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication

from pyprobe.plots.axis_controller import AxisController, AxisPinState


@pytest.fixture(scope="module")
def app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def plot_item(app):
    """Create a PlotItem for testing."""
    return pg.PlotItem()


@pytest.fixture
def controller(plot_item):
    """Create an AxisController for testing."""
    return AxisController(plot_item)


class TestAxisControllerInitialState:
    """Test initial state of AxisController."""
    
    def test_initial_x_not_pinned(self, controller):
        assert not controller.x_pinned
        assert not controller.is_pinned('x')
    
    def test_initial_y_not_pinned(self, controller):
        assert not controller.y_pinned
        assert not controller.is_pinned('y')


class TestAxisControllerSetPinned:
    """Test set_pinned functionality."""
    
    def test_set_x_pinned(self, controller):
        controller.set_pinned('x', True)
        assert controller.x_pinned
    
    def test_set_y_pinned(self, controller):
        controller.set_pinned('y', True)
        assert controller.y_pinned
    
    def test_unpin_x(self, controller):
        controller.set_pinned('x', True)
        controller.set_pinned('x', False)
        assert not controller.x_pinned
    
    def test_invalid_axis_raises(self, controller):
        with pytest.raises(ValueError):
            controller.set_pinned('z', True)


class TestAxisControllerToggle:
    """Test toggle functionality."""
    
    def test_toggle_x_pins(self, controller):
        controller.toggle_pin('x')
        assert controller.x_pinned
    
    def test_toggle_x_twice_unpins(self, controller):
        controller.toggle_pin('x')
        controller.toggle_pin('x')
        assert not controller.x_pinned


class TestAxisControllerReset:
    """Test reset functionality."""
    
    def test_reset_unpins_both(self, controller):
        controller.set_pinned('x', True)
        controller.set_pinned('y', True)
        controller.reset()
        assert not controller.x_pinned
        assert not controller.y_pinned


class TestAxisControllerSignals:
    """Test signal emission."""
    
    def test_emits_signal_on_pin(self, controller):
        signals_received = []
        controller.pin_state_changed.connect(
            lambda axis, pinned: signals_received.append((axis, pinned))
        )
        
        controller.set_pinned('x', True)
        
        assert ('x', True) in signals_received
    
    def test_no_signal_if_state_unchanged(self, controller):
        controller.set_pinned('x', True)
        
        signals_received = []
        controller.pin_state_changed.connect(
            lambda axis, pinned: signals_received.append((axis, pinned))
        )
        
        controller.set_pinned('x', True)  # Same state
        
        assert len(signals_received) == 0
```

---

## Manual Verification

After implementation, verify:

1. **Zoom pins axis**:
   - Probe a variable (array)
   - Use mouse scroll to zoom Y axis
   - Verify 🔒Y appears
   - New data arrives → Y axis does NOT autoscale

2. **Pan pins axis**:
   - Drag to pan X axis
   - Verify 🔒X appears

3. **Reset unpins**:
   - With axes pinned, press `R` key (requires keyboard task first)
   - Or call `controller.reset()` programmatically
   - Verify lock icons disappear
   - Verify autoscale resumes

---

## Success Criteria

- [ ] `AxisController` correctly tracks pin state
- [ ] Zooming/panning auto-pins affected axis
- [ ] `pin_state_changed` signal emitted on state change
- [ ] Lock icon visible when axis is pinned
- [ ] Lock icon disappears when unpinned
- [ ] `reset()` unpins both axes and autoscales
- [ ] Pin state survives data updates
- [ ] All unit tests pass
