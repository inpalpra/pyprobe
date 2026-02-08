"""
Layout manager for maximize/restore functionality.
Handles toggling a single panel to fill the container.
"""

from typing import Optional, Dict
from PyQt6.QtWidgets import QWidget, QGridLayout
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QRect, pyqtSignal, QObject

from pyprobe.logging import get_logger
logger = get_logger(__name__)


class LayoutManager(QObject):
    """Manages maximize/restore state for probe panels.
    
    Signals:
        layout_changed(bool): Emitted when maximize state changes (True=maximized)
    """
    
    layout_changed = pyqtSignal(bool)
    
    def __init__(self, container: QWidget):
        super().__init__(container)
        self._container = container
        self._maximized_panel: Optional[QWidget] = None
        self._hidden_panels: list = []
    
    def toggle_maximize(self, panel: QWidget) -> None:
        """Toggle maximize state for a panel.
        
        If panel is currently maximized, restore all.
        If another panel is maximized, restore that one and maximize this.
        If none maximized, maximize this panel.
        """
        if self._maximized_panel is panel:
            self.restore()
        elif self._maximized_panel is not None:
            self.restore()
            self._maximize(panel)
        else:
            self._maximize(panel)
    
    def _maximize(self, panel: QWidget) -> None:
        """Maximize a single panel, hiding others."""
        self._maximized_panel = panel
        self._hidden_panels = []
        
        # Find all sibling panels in the container's layout
        layout = self._container.layout()
        if layout is None:
            return
        
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if widget is None:
                continue
            if widget is not panel and widget.isVisible():
                widget.hide()
                self._hidden_panels.append(widget)
        
        logger.debug(f"Maximized panel, hid {len(self._hidden_panels)} others")
        self.layout_changed.emit(True)
    
    def restore(self) -> None:
        """Restore all panels to grid layout."""
        if self._maximized_panel is None:
            return
        
        # Show all hidden panels
        for widget in self._hidden_panels:
            widget.show()
        
        self._hidden_panels.clear()
        self._maximized_panel = None
        
        logger.debug("Restored all panels")
        self.layout_changed.emit(False)
    
    @property
    def is_maximized(self) -> bool:
        """Whether any panel is currently maximized."""
        return self._maximized_panel is not None
    
    @property
    def maximized_panel(self) -> Optional[QWidget]:
        """The currently maximized panel, or None."""
        return self._maximized_panel
