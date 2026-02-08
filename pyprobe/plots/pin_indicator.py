"""
Lock icon indicator for pinned axes.
Positioned inside the plot area, near the axis labels.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from pyprobe.logging import get_logger
logger = get_logger(__name__)


class PinIndicator(QWidget):
    """Lock icon overlay showing axis pin state.
    
    Shows 🔒X and/or 🔒Y when axes are pinned.
    Positioned at top-left of plot area.
    """
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._x_pinned = False
        self._y_pinned = False
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        font = QFont("JetBrains Mono", 9)
        
        self._x_label = QLabel("🔒X")
        self._x_label.setFont(font)
        self._x_label.setStyleSheet("color: #00ffff; background: rgba(13, 13, 13, 180); border-radius: 3px; padding: 1px 3px;")
        self._x_label.hide()
        layout.addWidget(self._x_label)
        
        self._y_label = QLabel("🔒Y")
        self._y_label.setFont(font)
        self._y_label.setStyleSheet("color: #00ffff; background: rgba(13, 13, 13, 180); border-radius: 3px; padding: 1px 3px;")
        self._y_label.hide()
        layout.addWidget(self._y_label)
        
        layout.addStretch()
        self.adjustSize()
    
    def set_x_pinned(self, pinned: bool) -> None:
        logger.debug(f"PinIndicator.set_x_pinned({pinned})")
        self._x_pinned = pinned
        self._x_label.setVisible(pinned)
        self.adjustSize()
        self.raise_()  # Ensure on top
        logger.debug(f"  _x_label visible: {self._x_label.isVisible()}, indicator visible: {self.isVisible()}")
    
    def set_y_pinned(self, pinned: bool) -> None:
        logger.debug(f"PinIndicator.set_y_pinned({pinned})")
        self._y_pinned = pinned
        self._y_label.setVisible(pinned)
        self.adjustSize()
        self.raise_()  # Ensure on top
        logger.debug(f"  _y_label visible: {self._y_label.isVisible()}, indicator visible: {self.isVisible()}")
    
    def update_state(self, axis: str, is_pinned: bool) -> None:
        logger.debug(f"PinIndicator.update_state(axis={axis}, is_pinned={is_pinned})")
        if axis == 'x':
            self.set_x_pinned(is_pinned)
        elif axis == 'y':
            self.set_y_pinned(is_pinned)
