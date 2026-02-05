"""Probe registry - central management of all probes. (STUB - implemented in Plan 5)"""
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor
from typing import Dict, Set, Optional
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.gui.probe_state import ProbeState


class ProbeRegistry(QObject):
    """Central registry for all active probes. STUB - full implementation in Plan 5."""

    # Signals
    probe_added = pyqtSignal(object, object)       # (anchor, color)
    probe_removed = pyqtSignal(object)             # (anchor,)
    probe_state_changed = pyqtSignal(object, object)  # (anchor, state)
    probe_invalidated = pyqtSignal(object)         # (anchor,)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._probes: Dict[ProbeAnchor, ProbeState] = {}

    def add_probe(self, anchor: ProbeAnchor) -> QColor:
        """Add probe and return assigned color. STUB."""
        raise NotImplementedError("Implement in Plan 5")

    def remove_probe(self, anchor: ProbeAnchor) -> None:
        """Remove probe. STUB."""
        raise NotImplementedError("Implement in Plan 5")

    def get_state(self, anchor: ProbeAnchor) -> Optional[ProbeState]:
        """Get probe state. STUB."""
        return self._probes.get(anchor)

    @property
    def active_anchors(self) -> Set[ProbeAnchor]:
        """Return set of all active anchors."""
        return set(self._probes.keys())
