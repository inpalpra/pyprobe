"""
Code gutter widget showing line numbers and probe indicators.

This widget displays:
- Line numbers synced with the code viewer
- Eye icons for lines with active probes
- Color-matched indicators for probe colors
"""

from typing import Optional, Dict
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QSize, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QFontMetricsF
)


class CodeGutter(QWidget):
    """Gutter widget showing line numbers and probe eye icons.

    This widget is designed to be placed alongside a QPlainTextEdit
    (CodeViewer) and syncs its scrolling via the updateRequest signal.

    Features:
    - Line numbers in muted gray
    - Eye icon (drawn as ellipse) for probed lines
    - Color-matched to probe color
    - Auto-width based on line count
    """

    def __init__(self, code_viewer, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._code_viewer = code_viewer
        self._probed_lines: Dict[int, QColor] = {}  # line number -> color

        # Configure font to match code viewer
        font = QFont("Menlo", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.setFont(font)

        # Connect to code viewer signals for sync
        self._code_viewer.blockCountChanged.connect(self._update_width)
        self._code_viewer.updateRequest.connect(self._on_update_request)

        # Set dark background
        self.setStyleSheet("""
            QWidget {
                background-color: #0a0a0a;
            }
        """)

        # Initial width calculation
        self._update_width()

    def _update_width(self) -> None:
        """Update gutter width based on line count."""
        digits = len(str(max(1, self._code_viewer.blockCount())))
        fm = QFontMetricsF(self.font())

        # Width: digits + padding + eye icon space
        char_width = fm.horizontalAdvance('9')
        # Left padding + digits + space + eye icon + right padding
        width = int(8 + (digits * char_width) + 4 + 16 + 8)

        self.setFixedWidth(width)

    def _on_update_request(self, rect, dy) -> None:
        """Handle scroll updates from code viewer."""
        if dy:
            self.scroll(0, dy)
        else:
            self.update(0, rect.y(), self.width(), rect.height())

    def set_probed_line(self, line: int, color: QColor) -> None:
        """Mark a line as having an active probe.

        Args:
            line: Line number (1-indexed)
            color: Color for the probe indicator
        """
        self._probed_lines[line] = color
        self.update()

    def clear_probed_line(self, line: int) -> None:
        """Remove probe indicator from a line.

        Args:
            line: Line number (1-indexed)
        """
        self._probed_lines.pop(line, None)
        self.update()

    def clear_all_probes(self) -> None:
        """Remove all probe indicators."""
        self._probed_lines.clear()
        self.update()

    def sizeHint(self) -> QSize:
        """Return the preferred size."""
        return QSize(self.width(), 0)

    def paintEvent(self, event) -> None:
        """Paint line numbers and probe indicators."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill background
        painter.fillRect(event.rect(), QColor("#0a0a0a"))

        # Get visible blocks
        block = self._code_viewer.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self._code_viewer.blockBoundingGeometry(block)
                  .translated(self._code_viewer.contentOffset()).top())
        bottom = top + int(self._code_viewer.blockBoundingRect(block).height())

        fm = QFontMetricsF(self.font())
        char_width = fm.horizontalAdvance('9')
        digits = len(str(max(1, self._code_viewer.blockCount())))

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                line_number = block_number + 1

                # Draw line number (right-aligned in digit area)
                painter.setPen(QColor("#666666"))
                number_rect = QRectF(
                    8,  # left padding
                    top,
                    digits * char_width,
                    fm.height()
                )
                painter.drawText(
                    number_rect,
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    str(line_number)
                )

                # Draw eye icon if this line has a probe
                if line_number in self._probed_lines:
                    color = self._probed_lines[line_number]
                    self._draw_eye_icon(
                        painter,
                        8 + (digits * char_width) + 8,  # x position after line number
                        top + (fm.height() / 2),        # y center
                        color
                    )

            block = block.next()
            top = bottom
            bottom = top + int(self._code_viewer.blockBoundingRect(block).height())
            block_number += 1

        painter.end()

    def _draw_eye_icon(
        self,
        painter: QPainter,
        x: float,
        y: float,
        color: QColor
    ) -> None:
        """Draw an eye icon (simplified as colored ellipse).

        Args:
            painter: QPainter to draw with
            x: X position (left edge)
            y: Y position (vertical center)
            color: Color for the eye icon
        """
        # Draw outer ellipse (eye shape)
        eye_width = 12
        eye_height = 6

        painter.setPen(QPen(color, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(
            QRectF(x, y - eye_height / 2, eye_width, eye_height)
        )

        # Draw pupil (inner filled circle)
        pupil_radius = 2
        painter.setBrush(QBrush(color))
        painter.drawEllipse(
            QRectF(
                x + (eye_width / 2) - pupil_radius,
                y - pupil_radius,
                pupil_radius * 2,
                pupil_radius * 2
            )
        )
