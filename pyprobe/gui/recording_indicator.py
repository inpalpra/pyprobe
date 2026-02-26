"""
RecordingIndicator — small floating frameless widget that signals recording is active.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class RecordingIndicator(QWidget):
    """Small always-on-top frameless widget showing '● Recording Steps'.

    Shown when recording starts, hidden when recording stops or the dialog closes.
    The instance is reused across sessions — shown and hidden rather than
    created and destroyed.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint,
        )
        self._shown: bool = False
        self._setup_ui()
        self.hide()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        dot = QLabel("●")
        dot.setStyleSheet("color: #ff3333; font-size: 14px;")
        layout.addWidget(dot)

        text = QLabel("Recording Steps")
        font = QFont()
        font.setBold(True)
        text.setFont(font)
        layout.addWidget(text)

        self.setStyleSheet(
            "background-color: #2a2a2a; color: #ffffff; border-radius: 4px;"
        )
        self.adjustSize()

    # ── Public API ────────────────────────────────────────────────────────────

    def show_indicator(self) -> None:
        """Make the indicator visible."""
        self._shown = True
        self.show()

    def hide_indicator(self) -> None:
        """Hide the indicator."""
        self._shown = False
        self.hide()

    @property
    def is_shown(self) -> bool:
        """True if the indicator is currently in the shown state."""
        return self._shown
