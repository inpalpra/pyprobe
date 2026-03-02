"""
Layout manager for maximize/restore functionality.
Handles toggling a single panel to fill the container.
"""

from enum import Enum, auto
from typing import Optional, Dict, List, Tuple
from PyQt6.QtWidgets import QWidget, QGridLayout
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QRect, pyqtSignal, QObject

from pyprobe.logging import get_logger
logger = get_logger(__name__)


class MaximizeState(Enum):
    """Enumeration of maximization states for the 3-stage cycle."""
    NORMAL = auto()
    CONTAINER = auto()
    FULL = auto()


class LayoutManager(QObject):
    """Manages maximize/restore state for probe panels.
    
    Signals:
        layout_changed(bool): Emitted when maximize state changes (True=maximized)
        full_maximize_toggled(bool): Emitted when entering/exiting full maximize mode
        panel_park_requested(object): Emitted when a panel should be parked (passes ProbeAnchor)
        panel_unpark_requested(object): Emitted when a panel should be unparked (passes ProbeAnchor)
    """
    
    layout_changed = pyqtSignal(bool)
    full_maximize_toggled = pyqtSignal(bool)
    panel_park_requested = pyqtSignal(object)  # ProbeAnchor
    panel_unpark_requested = pyqtSignal(object)  # ProbeAnchor
    
    def __init__(self, container: QWidget):
        super().__init__(container)
        self._container = container
        self._maximized_panel: Optional[QWidget] = None
        self._hidden_panels: List[Tuple[QWidget, object]] = []  # list of (panel, anchor) tuples
        self._state = MaximizeState.NORMAL
    
    def toggle_maximize(self, panel: QWidget) -> None:
        """Toggle maximize state for a panel through the 3-stage cycle.
        
        Cycle: NORMAL -> CONTAINER -> FULL -> NORMAL
        """
        if self._state == MaximizeState.NORMAL:
            self._enter_container_maximize(panel)
        elif self._state == MaximizeState.CONTAINER:
            if self._maximized_panel is panel:
                self._enter_full_maximize()
            else:
                # Switch maximize focus to another panel
                self.restore()
                self._enter_container_maximize(panel)
        elif self._state == MaximizeState.FULL:
            self.restore()
    
    def _enter_container_maximize(self, panel: QWidget) -> None:
        """Maximize a single panel within the container, parking others."""
        self._maximized_panel = panel
        self._hidden_panels = []
        self._state = MaximizeState.CONTAINER
        
        # Get all panels from container's _panels dict
        panels_dict = getattr(self._container, '_panels', None)
        if panels_dict is None:
            logger.warning("Container has no _panels dict, falling back to layout iteration")
            return
        
        for anchor, panel_list in panels_dict.items():
            for widget in panel_list:
                if widget is not panel and widget.isVisible():
                    self._hidden_panels.append((widget, anchor))
                    self.panel_park_requested.emit(anchor)
        
        logger.debug(f"Entered CONTAINER maximize for panel {panel}")
        self.layout_changed.emit(True)
    
    def _enter_full_maximize(self) -> None:
        """Enter full maximize mode, hiding non-graph UI components."""
        if self._state != MaximizeState.CONTAINER:
            return
            
        self._state = MaximizeState.FULL
        logger.debug("Entered FULL maximize mode")
        self.full_maximize_toggled.emit(True)
    
    def restore(self) -> None:
        """Restore all parked panels and exit any maximization state."""
        if self._state == MaximizeState.NORMAL:
            return
            
        if self._state == MaximizeState.FULL:
            self.full_maximize_toggled.emit(False)
        
        # Unpark all hidden panels
        for widget, anchor in self._hidden_panels:
            if anchor is not None:
                self.panel_unpark_requested.emit(anchor)
            else:
                widget.show()
        
        self._hidden_panels.clear()
        self._maximized_panel = None
        self._state = MaximizeState.NORMAL
        
        logger.debug("Restored to NORMAL layout")
        self.layout_changed.emit(False)
    
    @property
    def is_maximized(self) -> bool:
        """Whether any panel is currently maximized (CONTAINER or FULL)."""
        return self._state != MaximizeState.NORMAL
    
    @property
    def state(self) -> MaximizeState:
        """The current maximization state."""
        return self._state
    
    @property
    def maximized_panel(self) -> Optional[QWidget]:
        """The currently maximized panel, or None."""
        return self._maximized_panel
