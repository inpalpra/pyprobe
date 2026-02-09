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
        panel_park_requested(object): Emitted when a panel should be parked (passes ProbeAnchor)
        panel_unpark_requested(object): Emitted when a panel should be unparked (passes ProbeAnchor)
    """
    
    layout_changed = pyqtSignal(bool)
    panel_park_requested = pyqtSignal(object)  # ProbeAnchor
    panel_unpark_requested = pyqtSignal(object)  # ProbeAnchor
    
    def __init__(self, container: QWidget):
        super().__init__(container)
        self._container = container
        self._maximized_panel: Optional[QWidget] = None
        self._hidden_panels: list = []  # list of (panel, anchor) tuples
        self._get_anchor_for_panel = None  # Callback to get anchor from panel
    
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
        """Maximize a single panel, parking others to dock bar."""
        self._maximized_panel = panel
        self._hidden_panels = []
        
        # Get all panels from container's _panels dict (more reliable than layout iteration)
        panels_dict = getattr(self._container, '_panels', None)
        if panels_dict is None:
            logger.warning("Container has no _panels dict, falling back to layout iteration")
            return
        
        for anchor, widget in panels_dict.items():
            if widget is not panel and widget.isVisible():
                self._hidden_panels.append((widget, anchor))
                self.panel_park_requested.emit(anchor)
        
        logger.debug(f"Maximized panel, parked {len(self._hidden_panels)} others")
        self.layout_changed.emit(True)
    
    def restore(self) -> None:
        """Restore all parked panels from dock bar."""
        if self._maximized_panel is None:
            return
        
        # Unpark all hidden panels
        for widget, anchor in self._hidden_panels:
            if anchor is not None:
                self.panel_unpark_requested.emit(anchor)
            else:
                widget.show()
        
        self._hidden_panels.clear()
        self._maximized_panel = None
        
        logger.debug("Restored all panels from dock bar")
        self.layout_changed.emit(False)
    
    @property
    def is_maximized(self) -> bool:
        """Whether any panel is currently maximized."""
        return self._maximized_panel is not None
    
    @property
    def maximized_panel(self) -> Optional[QWidget]:
        """The currently maximized panel, or None."""
        return self._maximized_panel
