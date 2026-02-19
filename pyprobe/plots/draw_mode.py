"""
Draw mode enum and helper for line-plot curve rendering.

Supports three modes per curve: LINE (pen only), DOTS (filled squares only),
BOTH (pen + filled squares). Used by WaveformWidget and ComplexWidget subclasses.
"""

from enum import Enum, auto
import pyqtgraph as pg


class DrawMode(Enum):
    LINE = auto()   # pen only, no symbols
    DOTS = auto()   # no pen, filled squares only
    BOTH = auto()   # pen + filled squares


def apply_draw_mode(curve: pg.PlotDataItem, mode: DrawMode, color: str,
                    pen_width: float = 1.5) -> None:
    """Configure a pyqtgraph PlotDataItem for the given draw mode.

    Args:
        curve: The PlotDataItem to configure.
        mode: Which rendering mode to use.
        color: Hex color string (e.g., '#00ffff').
        pen_width: Line width when pen is active.
    """
    if mode == DrawMode.LINE:
        curve.setPen(pg.mkPen(color, width=pen_width))
        curve.setSymbol(None)
    elif mode == DrawMode.DOTS:
        curve.setPen(None)
        curve.setSymbol('s')  # filled square
        curve.setSymbolPen(None)
        curve.setSymbolBrush(color)
        curve.setSymbolSize(5)
    elif mode == DrawMode.BOTH:
        curve.setPen(pg.mkPen(color, width=pen_width))
        curve.setSymbol('s')  # filled square
        curve.setSymbolPen(None)
        curve.setSymbolBrush(color)
        curve.setSymbolSize(4)
