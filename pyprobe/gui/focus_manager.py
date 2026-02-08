"""
Focus manager for probe panels.
Tracks which panel has keyboard focus and handles Tab cycling.
"""

from typing import Optional, List
from PyQt6.QtCore import QObject, pyqtSignal

from pyprobe.logging import get_logger
logger = get_logger(__name__)


class FocusManager(QObject):
    """Manages keyboard focus across probe panels.
    
    Only one panel can have focus at a time.
    Supports Tab cycling through panels in order.
    
    Signals:
        focus_changed(object): Emitted when focus changes (panel or None)
    """
    
    focus_changed = pyqtSignal(object)
    
    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self._panels: List = []
        self._focused: Optional[object] = None
    
    def register_panel(self, panel) -> None:
        """Register a panel for focus management."""
        if panel not in self._panels:
            self._panels.append(panel)
            logger.debug(f"Panel registered, total: {len(self._panels)}")
    
    def unregister_panel(self, panel) -> None:
        """Unregister a panel from focus management."""
        if panel in self._panels:
            self._panels.remove(panel)
            if self._focused is panel:
                self._focused = None
                self.focus_changed.emit(None)
            logger.debug(f"Panel unregistered, total: {len(self._panels)}")
    
    def set_focus(self, panel) -> None:
        """Set focus to a specific panel."""
        if panel not in self._panels:
            return
        
        old = self._focused
        if old is panel:
            return
        
        self._focused = panel
        self.focus_changed.emit(panel)
        logger.debug(f"Focus changed to panel {self._panels.index(panel)}")
    
    def clear_focus(self) -> None:
        """Clear focus from all panels."""
        if self._focused is not None:
            self._focused = None
            self.focus_changed.emit(None)
            logger.debug("Focus cleared")
    
    def focus_next(self) -> None:
        """Cycle focus to the next panel (Tab behavior)."""
        if not self._panels:
            return
        
        if self._focused is None:
            self.set_focus(self._panels[0])
        else:
            try:
                idx = self._panels.index(self._focused)
                next_idx = (idx + 1) % len(self._panels)
                self.set_focus(self._panels[next_idx])
            except ValueError:
                self.set_focus(self._panels[0])
    
    @property
    def focused_panel(self):
        """The currently focused panel, or None."""
        return self._focused
    
    @property
    def panel_count(self) -> int:
        """Number of registered panels."""
        return len(self._panels)
