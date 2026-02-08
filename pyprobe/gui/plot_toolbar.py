"""
Translucent hover toolbar for plot interaction modes.
Appears on mouse hover, fades to max 40% opacity.
"""

from enum import Enum, auto
import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QGraphicsOpacityEffect
from PyQt6.QtCore import pyqtSignal, Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon

from pyprobe.logging import get_logger
logger = get_logger(__name__)


class InteractionMode(Enum):
    POINTER = auto()
    PAN = auto()
    ZOOM = auto()
    ZOOM_X = auto()
    ZOOM_Y = auto()


class PlotToolbar(QWidget):
    """Translucent toolbar with plot interaction mode buttons.

    Signals:
        mode_changed(InteractionMode): Emitted when interaction mode changes
        reset_requested(): Emitted when reset button clicked
    """

    mode_changed = pyqtSignal(object)  # InteractionMode
    reset_requested = pyqtSignal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._current_mode = InteractionMode.POINTER
        self._buttons = {}
        self._setup_ui()
        self._setup_opacity()

    def _setup_ui(self) -> None:
        """Create toolbar buttons."""
        self.setStyleSheet("""
            QWidget {
                background: transparent;
            }
            QPushButton {
                background-color: rgba(26, 26, 46, 200);
                border: 1px solid #00ffff;
                border-radius: 4px;
                padding: 4px;
                min-width: 28px;
                min-height: 28px;
                max-width: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 255, 60);
            }
            QPushButton:checked {
                background-color: rgba(0, 255, 255, 100);
                border: 2px solid #00ffff;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        icon_dir = os.path.join(os.path.dirname(__file__), 'icons')

        # Mode buttons (checkable, exclusive)
        modes = [
            (InteractionMode.POINTER, 'icon_pointer.svg', 'Pointer (default)'),
            (InteractionMode.PAN, 'icon_pan.svg', 'Pan (drag to pan)'),
            (InteractionMode.ZOOM, 'icon_zoom.svg', 'Zoom (drag rectangle)'),
            (InteractionMode.ZOOM_X, 'icon_zoom_x.svg', 'Zoom X only'),
            (InteractionMode.ZOOM_Y, 'icon_zoom_y.svg', 'Zoom Y only'),
        ]

        for mode, icon_file, tooltip in modes:
            btn = QPushButton(self)
            icon_path = os.path.join(icon_dir, icon_file)
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
            else:
                # Fallback text
                btn.setText(mode.name[0])
                btn.setStyleSheet(btn.styleSheet() + "QPushButton { color: #00ffff; font-size: 10px; }")
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setChecked(mode == InteractionMode.POINTER)
            btn.clicked.connect(lambda checked, m=mode: self._on_mode_clicked(m))
            layout.addWidget(btn)
            self._buttons[mode] = btn

        # Reset button (not checkable)
        self._reset_btn = QPushButton(self)
        icon_path = os.path.join(icon_dir, 'icon_reset.svg')
        if os.path.exists(icon_path):
            self._reset_btn.setIcon(QIcon(icon_path))
        else:
            self._reset_btn.setText("R")
            self._reset_btn.setStyleSheet(self._reset_btn.styleSheet() + "QPushButton { color: #ff00ff; font-size: 10px; }")
        self._reset_btn.setToolTip('Reset (unpin + autoscale)')
        self._reset_btn.setCheckable(False)
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        layout.addWidget(self._reset_btn)

        self.adjustSize()

    def _setup_opacity(self) -> None:
        """Setup opacity effect for fade in/out."""
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_anim.setDuration(150)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.hide()

    def _on_mode_clicked(self, mode: InteractionMode) -> None:
        """Handle mode button click."""
        self._current_mode = mode
        # Update checked state
        for m, btn in self._buttons.items():
            btn.setChecked(m == mode)
        self.mode_changed.emit(mode)
        logger.debug(f"Interaction mode changed to {mode.name}")

    def _on_reset_clicked(self) -> None:
        """Handle reset button click."""
        self.reset_requested.emit()
        logger.debug("Reset requested from toolbar")

    def show_on_hover(self) -> None:
        """Fade in to 40% opacity."""
        self.show()
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(0.4)
        self._fade_anim.start()

    def hide_on_leave(self) -> None:
        """Fade out to 0% opacity."""
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()

    def revert_to_pointer(self) -> None:
        """Revert to pointer mode (called after pan/zoom action)."""
        self._on_mode_clicked(InteractionMode.POINTER)

    def set_mode(self, mode: InteractionMode) -> None:
        """Set current mode programmatically."""
        self._on_mode_clicked(mode)

    @property
    def current_mode(self) -> InteractionMode:
        return self._current_mode
