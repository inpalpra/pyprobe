"""
Bottom dock bar for parked (minimized) probe panels.
Shows title + color dot for each parked panel.
Click to restore.
"""

from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QFrame, QLabel, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush

from pyprobe.logging import get_logger
logger = get_logger(__name__)


class ColorDot(QWidget):
    """Small colored circle indicator."""
    
    def __init__(self, color: QColor, parent: QWidget = None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(10, 10)
    
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(self._color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(1, 1, 8, 8)
        painter.end()


class DockBarItem(QFrame):
    """Single item in the dock bar representing a parked panel."""
    
    restore_requested = pyqtSignal()
    
    def __init__(self, title: str, color: QColor, parent: QWidget = None):
        super().__init__(parent)
        self._title = title
        self._color = color
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setStyleSheet("""
            DockBarItem {
                background-color: #1a1a2e;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 2px 6px;
            }
            DockBarItem:hover {
                border-color: #00ffff;
                background-color: #1a1a3e;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)
        
        # Color dot
        dot = ColorDot(self._color, self)
        layout.addWidget(dot)
        
        # Title
        label = QLabel(self._title)
        label.setFont(QFont("JetBrains Mono", 9))
        label.setStyleSheet("color: #cccccc; background: transparent; border: none;")
        layout.addWidget(label)
        
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            logger.debug(f"DockBarItem clicked: {self._title}")
            self.restore_requested.emit()
        super().mousePressEvent(event)


class DockBar(QWidget):
    """Bottom bar showing parked/minimized probe panels.
    
    Signals:
        panel_restore_requested(str): Emitted when user clicks item to restore (anchor_key)
    """
    
    panel_restore_requested = pyqtSignal(str)
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._items: Dict[str, DockBarItem] = {}
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        self.setStyleSheet("""
            DockBar {
                background-color: #0a0a1a;
                border-top: 1px solid #333333;
            }
        """)
        self.setFixedHeight(40)
        
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 4)
        self._layout.setSpacing(6)
        self._layout.addStretch()
        
        self.hide()  # Auto-hide when empty
    
    def add_panel(self, anchor_key: str, title: str, color: QColor) -> None:
        """Add a parked panel to the dock bar."""
        if anchor_key in self._items:
            return
        
        item = DockBarItem(title, color, self)
        item.restore_requested.connect(lambda key=anchor_key: self._on_restore(key))
        
        # Insert before the stretch
        self._layout.insertWidget(self._layout.count() - 1, item)
        self._items[anchor_key] = item
        
        self.setVisible(True)
        logger.debug(f"Panel parked: {title} ({anchor_key})")
    
    def remove_panel(self, anchor_key: str) -> None:
        """Remove a panel from the dock bar."""
        item = self._items.pop(anchor_key, None)
        if item is not None:
            self._layout.removeWidget(item)
            item.deleteLater()
            logger.debug(f"Panel unparked: {anchor_key}")
        
        if self.is_empty():
            self.hide()
    
    def _on_restore(self, anchor_key: str) -> None:
        """Handle restore request from dock bar item."""
        self.panel_restore_requested.emit(anchor_key)
    
    def is_empty(self) -> bool:
        """Whether the dock bar has no items."""
        return len(self._items) == 0
    
    def update_data(self, anchor_key: str, data) -> None:
        """Update data for a parked panel (for sparkline, future use)."""
        pass  # Sparkline is P1, not implemented yet
