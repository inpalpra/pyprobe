"""
Translucent hover toolbar for plot interaction modes.
Appears on mouse hover, fades to max 40% opacity.
"""

from enum import Enum, auto
import os
import re
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QGraphicsOpacityEffect
from PyQt6.QtCore import pyqtSignal, Qt, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QIcon, QColor, QPixmap

from pyprobe.logging import get_logger
logger = get_logger(__name__)

_BTN = 30
_ICON = 16


def _svg_icon(path: str, color: str) -> QIcon:
    """Load an SVG file, recolor all non-none stroke/fill to `color`, return QIcon."""
    try:
        with open(path, 'r') as f:
            data = f.read()
        # Replace all explicit colors; preserve stroke="none" / fill="none"
        data = re.sub(
            r'(stroke|fill)="(?!none)([^"]+)"',
            lambda m: f'{m.group(1)}="{color}"',
            data,
        )
        data = data.replace('currentColor', color)
        pixmap = QPixmap()
        pixmap.loadFromData(data.encode('utf-8'), 'SVG')
        return QIcon(pixmap)
    except Exception:
        return QIcon()


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
        self._icon_paths = {}  # mode/key -> path (or None if missing)
        self._setup_ui()
        self._setup_opacity()
        self._setup_theme()

    def _setup_ui(self) -> None:
        """Create toolbar buttons."""
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("PlotToolbar { background: transparent; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.setSizeConstraint(QHBoxLayout.SizeConstraint.SetFixedSize)

        icon_dir = os.path.join(os.path.dirname(__file__), 'icons')

        modes = [
            (InteractionMode.POINTER, 'icon_pointer.svg', 'Pointer (default)'),
            (InteractionMode.PAN, 'icon_pan.svg', 'Pan (drag to pan)'),
            (InteractionMode.ZOOM, 'icon_zoom.svg', 'Zoom (drag rectangle)'),
            (InteractionMode.ZOOM_X, 'icon_zoom_x.svg', 'Zoom X only'),
            (InteractionMode.ZOOM_Y, 'icon_zoom_y.svg', 'Zoom Y only'),
        ]

        for mode, icon_file, tooltip in modes:
            btn = QPushButton(self)
            btn.setFixedSize(_BTN, _BTN)
            btn.setIconSize(QSize(_ICON, _ICON))
            icon_path = os.path.join(icon_dir, icon_file)
            if os.path.exists(icon_path):
                self._icon_paths[mode] = icon_path
            else:
                self._icon_paths[mode] = None
                btn.setText(mode.name[0])
                btn.setObjectName("fallbackModeBtn")
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setChecked(mode == InteractionMode.POINTER)
            btn.clicked.connect(lambda checked, m=mode: self._on_mode_clicked(m))
            layout.addWidget(btn)
            self._buttons[mode] = btn

        # Reset button (not checkable)
        self._reset_btn = QPushButton(self)
        self._reset_btn.setFixedSize(_BTN, _BTN)
        self._reset_btn.setIconSize(QSize(_ICON, _ICON))
        reset_path = os.path.join(icon_dir, 'icon_reset.svg')
        if os.path.exists(reset_path):
            self._icon_paths['reset'] = reset_path
        else:
            self._icon_paths['reset'] = None
            self._reset_btn.setText("R")
            self._reset_btn.setObjectName("fallbackResetBtn")
        self._reset_btn.setToolTip('Reset (unpin + autoscale)')
        self._reset_btn.setCheckable(False)
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        layout.addWidget(self._reset_btn)

    def _setup_opacity(self) -> None:
        """Setup opacity effect for fade in/out."""
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_anim.setDuration(150)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.hide()

    def _setup_theme(self) -> None:
        """Connect to ThemeManager and apply the current theme."""
        from pyprobe.gui.theme.theme_manager import ThemeManager
        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.current)

    def _apply_theme(self, theme) -> None:
        """Rebuild the toolbar stylesheet and recolor icons from theme colors."""
        c = theme.colors
        accent = c['accent_primary']
        accent2 = c['accent_secondary']
        
        # Use a theme-appropriate color instead of harsh black
        icon_color = c['text_primary']

        # Recolor all SVG icons with the theme's text color
        for mode, btn in self._buttons.items():
            path = self._icon_paths.get(mode)
            if path:
                btn.setIcon(_svg_icon(path, icon_color))
        reset_path = self._icon_paths.get('reset')
        if reset_path:
            self._reset_btn.setIcon(_svg_icon(reset_path, icon_color))

        # Derive semi-transparent overlay background from bg_darkest
        bg_color = QColor(c['bg_darkest'])
        bg_r, bg_g, bg_b = bg_color.red(), bg_color.green(), bg_color.blue()

        # Derive accent RGB components for rgba() expressions
        ac_color = QColor(accent)
        ac_r, ac_g, ac_b = ac_color.red(), ac_color.green(), ac_color.blue()

        self.setStyleSheet(f"""
            PlotToolbar {{
                background-color: rgba({bg_r}, {bg_g}, {bg_b}, 230);
                border: 1px solid {c['border_medium']};
                border-radius: 6px;
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: rgba({ac_r}, {ac_g}, {ac_b}, 40);
            }}
            QPushButton:checked {{
                background-color: rgba({ac_r}, {ac_g}, {ac_b}, 80);
            }}
            QPushButton#fallbackModeBtn {{
                color: {accent};
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton#fallbackResetBtn {{
                color: {accent2};
                font-size: 11px;
                font-weight: bold;
            }}
        """)

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
        self.raise_()  # Ensure topmost z-order
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

    def enterEvent(self, event) -> None:
        """Full opacity when hovering directly over toolbar."""
        super().enterEvent(event)
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def leaveEvent(self, event) -> None:
        """Return to 40% opacity when leaving toolbar."""
        super().leaveEvent(event)
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(0.4)
        self._fade_anim.start()
