"""Color manager - assigns colors to probes. (STUB - implemented in Plan 5)"""
from PyQt6.QtGui import QColor
from typing import Dict, Optional
from pyprobe.core.anchor import ProbeAnchor


class ColorManager:
    """Manages probe color assignments. STUB - full implementation in Plan 5."""

    # Limited palette (brutal teardown requirement)
    PALETTE = [
        QColor('#00ffff'),  # cyan (primary)
        QColor('#ff00ff'),  # magenta
        QColor('#00ff00'),  # green
        QColor('#ffff00'),  # yellow
        QColor('#ff8800'),  # orange
    ]

    def __init__(self):
        self._assignments: Dict[ProbeAnchor, int] = {}

    def get_color(self, anchor: ProbeAnchor) -> QColor:
        """Get color for anchor. STUB."""
        raise NotImplementedError("Implement in Plan 5")

    def release_color(self, anchor: ProbeAnchor) -> None:
        """Release color when probe removed. STUB."""
        raise NotImplementedError("Implement in Plan 5")
