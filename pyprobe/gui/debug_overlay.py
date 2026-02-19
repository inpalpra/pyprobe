"""
Debug overlay for visualizing layout regions.

Toggle with Ctrl+Shift+D in a ProbePanel.
Draws semi-transparent colored bounding boxes over named regions
(toolbar, plot area, pin buttons) so layout intent is immediately visible.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QFont, QPen
from PyQt6.QtCore import Qt, QRect, QRectF


# Region definitions: (label, colour)
_REGION_STYLES = {
    'toolbar':   QColor(255, 165,   0,  60),   # Orange
    'plot_area': QColor(  0, 255,   0,  40),   # Green
    'x_pin':     QColor(255,   0,   0,  80),   # Red
    'y_pin':     QColor(  0, 100, 255,  80),   # Blue
}

_BORDER_STYLES = {
    'toolbar':   QColor(255, 165,   0, 180),
    'plot_area': QColor(  0, 255,   0, 140),
    'x_pin':     QColor(255,   0,   0, 200),
    'y_pin':     QColor(  0, 100, 255, 200),
}


class DebugOverlay(QWidget):
    """Transparent overlay that paints named bounding boxes.

    Call ``set_regions(dict[str, QRect|QRectF])`` to update the
    regions to draw.  Keys should match ``_REGION_STYLES`` above;
    unknown keys get a default grey colour.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._regions: dict[str, QRect | QRectF] = {}
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

    # ------------------------------------------------------------------
    def set_regions(self, regions: dict) -> None:
        """Update the set of named regions to draw.

        Args:
            regions: Mapping of region name → QRect/QRectF in
                     *this widget's* coordinate system.
        """
        self._regions = dict(regions)
        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._regions:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = QFont("JetBrains Mono", 9, QFont.Weight.Bold)
        painter.setFont(font)

        default_fill   = QColor(128, 128, 128, 40)
        default_border = QColor(128, 128, 128, 140)

        for name, rect in self._regions.items():
            fill   = _REGION_STYLES.get(name, default_fill)
            border = _BORDER_STYLES.get(name, default_border)

            r = QRectF(rect) if isinstance(rect, QRect) else rect

            painter.setBrush(fill)
            painter.setPen(QPen(border, 2))
            painter.drawRect(r)

            # Label
            painter.setPen(QPen(border.lighter(140), 1))
            painter.drawText(r.adjusted(4, 2, 0, 0), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, name)

        painter.end()
