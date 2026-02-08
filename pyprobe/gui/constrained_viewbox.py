"""
Custom ViewBox that supports axis-constrained zoom modes.
"""

import pyqtgraph as pg
from pyqtgraph import Point
from PyQt6.QtCore import Qt

from pyprobe.logging import get_logger
logger = get_logger(__name__)


class ConstrainedViewBox(pg.ViewBox):
    """ViewBox subclass that can constrain zoom to X or Y axis only.
    
    When zoom_axis is set to 'x', only X-axis zooming is allowed.
    When zoom_axis is set to 'y', only Y-axis zooming is allowed.
    When zoom_axis is None (default), normal zoom behavior applies.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zoom_axis = None  # None, 'x', or 'y'
        self._saved_range = None  # Store range before constrained zoom
    
    def setZoomAxis(self, axis: str = None):
        """Set which axis to zoom. None = both, 'x' = X only, 'y' = Y only."""
        self._zoom_axis = axis
        if axis:
            # Save current ranges when entering constrained mode
            self._saved_range = self.viewRange()
            logger.debug(f"ConstrainedViewBox: zoom axis set to {axis}, saved range: {self._saved_range}")
    
    def setRange(self, rect=None, xRange=None, yRange=None, padding=None, 
                 update=True, disableAutoRange=True):
        """Override setRange to constrain to specified axis."""
        if self._zoom_axis and self._saved_range:
            if self._zoom_axis == 'x' and yRange is None and rect is not None:
                # Only allow X to change, restore Y
                yRange = self._saved_range[1]
                logger.debug(f"ConstrainedViewBox: constraining to X, restoring Y to {yRange}")
            elif self._zoom_axis == 'y' and xRange is None and rect is not None:
                # Only allow Y to change, restore X
                xRange = self._saved_range[0]
                logger.debug(f"ConstrainedViewBox: constraining to Y, restoring X to {xRange}")
        
        super().setRange(rect=rect, xRange=xRange, yRange=yRange, padding=padding,
                        update=update, disableAutoRange=disableAutoRange)
        
        # Update saved range for the moving axis
        if self._zoom_axis == 'x':
            x, _ = self.viewRange()
            self._saved_range = [x, self._saved_range[1]]
        elif self._zoom_axis == 'y':
            _, y = self.viewRange()
            self._saved_range = [self._saved_range[0], y]
