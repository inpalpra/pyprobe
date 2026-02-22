"""
Lock icon buttons for pinned axes.
- X lock positioned near X axis (bottom-left of plot)
- Y lock positioned near Y axis (top-left of plot)
- Always visible: translucent when inactive, opaque when active
- Clickable to toggle pin state
"""

import os
from PyQt6.QtWidgets import QWidget, QPushButton, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QIcon, QRegion

from pyprobe.logging import get_logger
logger = get_logger(__name__)


class PinButton(QPushButton):
    """A single pin button with opacity toggle."""

    def __init__(self, icon_path: str, tooltip: str, parent: QWidget = None):
        super().__init__(parent)
        self._pinned = False

        # Setup appearance
        self.setFixedSize(20, 20)
        self.setCheckable(True)
        self.setToolTip(tooltip)

        if os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))

        # Setup opacity effect
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._set_opacity(False)

        from pyprobe.gui.theme.theme_manager import ThemeManager
        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.current)

    def _apply_theme(self, theme) -> None:
        c = theme.colors
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(13, 13, 13, 180);
                border: 1px solid {c['accent_primary']};
                border-radius: 3px;
                padding: 2px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 255, 255, 60);
            }}
            QPushButton:checked {{
                background-color: rgba(0, 255, 255, 100);
                border: 2px solid {c['accent_primary']};
            }}
            QToolTip {{
                background-color: {c['bg_medium']};
                color: {c['text_primary']};
                border: 1px solid {c['accent_primary']};
                padding: 4px 8px;
                border-radius: 4px;
            }}
        """)
    
    def _set_opacity(self, active: bool) -> None:
        """Set opacity based on pin state."""
        self._opacity_effect.setOpacity(1.0 if active else 0.4)
    
    def set_pinned(self, pinned: bool) -> None:
        """Update the button's pinned visual state."""
        self._pinned = pinned
        self.setChecked(pinned)
        self._set_opacity(pinned)
    
    @property
    def is_pinned(self) -> bool:
        return self._pinned


class PinIndicator(QWidget):
    """Lock icon buttons showing axis pin state.
    
    - X lock near bottom-left (near X axis)
    - Y lock near top-left (near Y axis)
    - Always visible, clickable to toggle
    
    Signals:
        x_pin_clicked(): Emitted when X lock button clicked
        y_pin_clicked(): Emitted when Y lock button clicked
    """
    
    x_pin_clicked = pyqtSignal()
    y_pin_clicked = pyqtSignal()
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._x_pinned = False
        self._y_pinned = False
        self._toolbar_rect = None  # Set by ProbePanel to avoid hardcoded offsets
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        # Don't block mouse events - we want buttons to be clickable
        self.setStyleSheet("background: transparent;")
        
        # Get icon paths
        icon_dir = os.path.join(os.path.dirname(__file__), '..', 'gui', 'icons')
        # If we're already in gui/icons parent, adjust path
        if not os.path.exists(icon_dir):
            icon_dir = os.path.join(os.path.dirname(__file__), 'icons')
        if not os.path.exists(icon_dir):
            # Fallback for plugin context
            icon_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'gui', 'icons')
        
        x_icon = os.path.join(icon_dir, 'icon_lock_x.svg')
        y_icon = os.path.join(icon_dir, 'icon_lock_y.svg')
        
        # Create X pin button
        self._x_btn = PinButton(x_icon, "Lock X axis (X key)", self)
        self._x_btn.clicked.connect(self._on_x_clicked)
        
        # Create Y pin button
        self._y_btn = PinButton(y_icon, "Lock Y axis (Y key)", self)
        self._y_btn.clicked.connect(self._on_y_clicked)
        
        # Set minimum size to contain both buttons with some margin
        self.setMinimumSize(100, 100)
    
    def set_toolbar_rect(self, rect) -> None:
        """Store the actual toolbar geometry for dynamic positioning.
        
        Called by ProbePanel.resizeEvent() so we can position the X lock
        button relative to the real toolbar instead of a hardcoded offset.
        
        Args:
            rect: QRect of the toolbar in parent (ProbePanel) coordinates.
        """
        self._toolbar_rect = rect
    
    def _on_x_clicked(self) -> None:
        logger.debug("X pin button clicked")
        self.x_pin_clicked.emit()
    
    def _on_y_clicked(self) -> None:
        logger.debug("Y pin button clicked")
        self.y_pin_clicked.emit()
    
    def update_layout(self, view_rect: QRectF) -> None:
        """Position buttons relative to the plot area.
        
        Args:
            view_rect: The main plot area (ViewBox) in parent coordinates.
        """
        # Y lock: Inside plot area at top-left
        y_x = view_rect.left() + 4
        y_y = view_rect.top() + 4
        self._y_btn.move(int(y_x), int(y_y))
        
        # X lock: extreme right of plot area, just above X axis
        x_x = view_rect.right() - self._x_btn.width() - 4
        x_y = view_rect.bottom() - self._x_btn.height() - 4
        self._x_btn.move(int(x_x), int(x_y))
        
        self._x_btn.raise_()
        self._y_btn.raise_()
        
        self._update_mask()

    def _update_mask(self) -> None:
        """Update mask to only allow input on buttons."""
        mask = QRegion(self._x_btn.geometry()) + QRegion(self._y_btn.geometry())
        self.setMask(mask)
    
    def set_x_pinned(self, pinned: bool) -> None:
        logger.debug(f"PinIndicator.set_x_pinned({pinned})")
        self._x_pinned = pinned
        self._x_btn.set_pinned(pinned)
    
    def set_y_pinned(self, pinned: bool) -> None:
        logger.debug(f"PinIndicator.set_y_pinned({pinned})")
        self._y_pinned = pinned
        self._y_btn.set_pinned(pinned)
    
    def update_state(self, axis: str, is_pinned: bool) -> None:
        logger.debug(f"PinIndicator.update_state(axis={axis}, is_pinned={is_pinned})")
        if axis == 'x':
            self.set_x_pinned(is_pinned)
        elif axis == 'y':
            self.set_y_pinned(is_pinned)
