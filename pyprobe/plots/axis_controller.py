"""
Axis pin state controller for PyQtGraph plots.
Manages AUTO/PINNED state for X and Y axes.
"""

from enum import Enum, auto
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
import pyqtgraph as pg

from pyprobe.logging import get_logger
logger = get_logger(__name__)


class AxisPinState(Enum):
    AUTO = auto()
    PINNED = auto()


class AxisController(QObject):
    """Manages axis pin state for a PlotItem.
    
    Signals:
        pin_state_changed(axis: str, is_pinned: bool)
    """
    
    pin_state_changed = pyqtSignal(str, bool)
    
    def __init__(self, plot_item: pg.PlotItem):
        super().__init__()
        self._plot_item = plot_item
        self._x_state = AxisPinState.AUTO
        self._y_state = AxisPinState.AUTO
        self._setup_signals()
    
    def _setup_signals(self) -> None:
        view_box = self._plot_item.getViewBox()
        view_box.sigRangeChangedManually.connect(self._on_manual_range_change)
    
    def _on_manual_range_change(self, mask: list) -> None:
        """Handle manual range change (zoom/pan). mask=[x_changed, y_changed]"""
        if len(mask) >= 1 and mask[0]:
            self.set_pinned('x', True)
        if len(mask) >= 2 and mask[1]:
            self.set_pinned('y', True)
    
    def is_pinned(self, axis: str) -> bool:
        if axis == 'x':
            return self._x_state == AxisPinState.PINNED
        elif axis == 'y':
            return self._y_state == AxisPinState.PINNED
        raise ValueError(f"Invalid axis: {axis}")
    
    def set_pinned(self, axis: str, pinned: bool) -> None:
        state = AxisPinState.PINNED if pinned else AxisPinState.AUTO
        changed = False
        if axis == 'x' and self._x_state != state:
            self._x_state = state
            changed = True
        elif axis == 'y' and self._y_state != state:
            self._y_state = state
            changed = True
        
        if changed:
            if pinned:
                self._plot_item.enableAutoRange(axis=axis, enable=False)
            else:
                self._plot_item.enableAutoRange(axis=axis, enable=True)
            self.pin_state_changed.emit(axis, pinned)
            logger.debug(f"Axis {axis} {'pinned' if pinned else 'unpinned'}")
    
    def toggle_pin(self, axis: str) -> None:
        self.set_pinned(axis, not self.is_pinned(axis))
    
    def reset(self) -> None:
        self.set_pinned('x', False)
        self.set_pinned('y', False)
        self._plot_item.autoRange()
    
    @property
    def x_pinned(self) -> bool:
        return self._x_state == AxisPinState.PINNED
    
    @property
    def y_pinned(self) -> bool:
        return self._y_state == AxisPinState.PINNED
