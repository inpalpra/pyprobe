"""
Custom PyQtGraph AxisItem with double-click editing support.
"""

import pyqtgraph as pg
from PyQt6.QtCore import pyqtSignal, QPointF
from PyQt6.QtWidgets import QGraphicsSceneMouseEvent

from pyprobe.logging import get_logger
logger = get_logger(__name__)


class EditableAxisItem(pg.AxisItem):
    """AxisItem that emits signals for double-click on tick labels.
    
    Signals:
        edit_min_requested(float): Double-click on first tick
        edit_max_requested(float): Double-click on last tick
    """
    
    edit_min_requested = pyqtSignal(float)
    edit_max_requested = pyqtSignal(float)
    
    def __init__(self, orientation, **kwargs):
        super().__init__(orientation, **kwargs)
        self.setAcceptHoverEvents(True)
    
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handle double-click on axis tick labels."""
        pos = event.pos()
        view_range = self.range
        
        if view_range is None or len(view_range) < 2:
            event.ignore()
            return
        
        min_val, max_val = view_range
        
        # Determine if click is near min or max end of axis
        if self.orientation == 'bottom' or self.orientation == 'top':
            # Horizontal axis: left=min, right=max
            rect = self.boundingRect()
            relative_pos = (pos.x() - rect.x()) / max(rect.width(), 1)
            if relative_pos < 0.3:
                logger.debug(f"Edit min requested on {self.orientation} axis: {min_val}")
                self.edit_min_requested.emit(min_val)
                event.accept()
                return
            elif relative_pos > 0.7:
                logger.debug(f"Edit max requested on {self.orientation} axis: {max_val}")
                self.edit_max_requested.emit(max_val)
                event.accept()
                return
        else:
            # Vertical axis: bottom=min, top=max
            rect = self.boundingRect()
            relative_pos = (pos.y() - rect.y()) / max(rect.height(), 1)
            if relative_pos > 0.7:  # Bottom of vertical = min
                logger.debug(f"Edit min requested on {self.orientation} axis: {min_val}")
                self.edit_min_requested.emit(min_val)
                event.accept()
                return
            elif relative_pos < 0.3:  # Top of vertical = max
                logger.debug(f"Edit max requested on {self.orientation} axis: {max_val}")
                self.edit_max_requested.emit(max_val)
                event.accept()
                return
        
        event.ignore()
