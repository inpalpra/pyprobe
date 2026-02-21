"""Thin clickable edge strip with a chevron glyph for collapsible panes."""

from typing import Optional
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QPainter, QFont, QColor

from .theme.theme_manager import ThemeManager


class EdgeStrip(QWidget):
    """A 20px-wide vertical bar with a centered chevron.

    Only shown when the parent pane is collapsed.  The chevron points
    inward (toward where the content would appear) to indicate "click
    to expand."

    Parameters
    ----------
    side : str
        ``"left"`` → chevron points right (▸).
        ``"right"`` → chevron points left (◂).
    tooltip : str
        Tooltip shown on hover.
    """

    clicked = pyqtSignal()

    def __init__(
        self,
        side: str = "left",
        tooltip: str = "Expand",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._side = side
        self._hovered = False

        self.setFixedWidth(20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)

        self._glyph = "\u25b8" if side == "left" else "\u25c2"

        self._bg_color = QColor("#0a0a0a")
        self._glyph_color = QColor("#666666")
        self._glyph_hover_color = QColor("#00ccff")
        self._border_color = QColor("#333333")

        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.current)

    # -- Qt overrides --------------------------------------------------------

    def sizeHint(self) -> QSize:
        return QSize(20, 100)

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.fillRect(self.rect(), self._bg_color)

        # Border on the content-facing edge
        p.setPen(self._border_color)
        if self._side == "left":
            p.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        else:
            p.drawLine(0, 0, 0, self.height())

        # Chevron
        color = self._glyph_hover_color if self._hovered else self._glyph_color
        p.setPen(color)
        font = QFont()
        font.setPixelSize(12)
        p.setFont(font)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._glyph)
        p.end()

    # -- Theme ---------------------------------------------------------------

    def _apply_theme(self, theme) -> None:
        c = theme.colors
        self._bg_color = QColor(c["bg_darkest"])
        self._glyph_color = QColor(c["text_muted"])
        self._glyph_hover_color = QColor(c["accent_primary"])
        self._border_color = QColor(c["border_default"])
        self.update()
