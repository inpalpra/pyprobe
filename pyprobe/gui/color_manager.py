"""Color manager - assigns colors to probes with LRU tracking."""
from collections import OrderedDict
from typing import Optional
from PyQt6.QtGui import QColor

from pyprobe.core.anchor import ProbeAnchor


class ColorManager:
    """
    Manages probe color assignments with LRU-based emphasis.

    Uses OrderedDict for LRU tracking - most recently accessed probes
    get full emphasis, older ones get de-emphasized.

    Limited palette enforces brutal teardown - when colors run out,
    user must remove old probes to add new ones.
    """

    # Limited palette (brutal teardown requirement)
    PALETTE = [
        QColor('#00ffff'),  # cyan (primary)
        QColor('#ff00ff'),  # magenta
        QColor('#00ff00'),  # green
        QColor('#ffff00'),  # yellow
        QColor('#ff8800'),  # orange
    ]

    def __init__(self):
        # OrderedDict for LRU tracking: anchor -> color index
        self._assignments: OrderedDict[ProbeAnchor, int] = OrderedDict()
        # Available indices for color recycling (stack)
        self._available_indices: list[int] = list(range(len(self.PALETTE) - 1, -1, -1))

    def get_color(self, anchor: ProbeAnchor) -> QColor:
        """
        Get or assign color for anchor.

        If already assigned, moves to end (most recent) and returns color.
        If new, assigns from available pool.

        Returns:
            QColor for the anchor

        Raises:
            ValueError: If no colors available (palette exhausted)
        """
        if anchor in self._assignments:
            # Move to end (most recent access)
            self._assignments.move_to_end(anchor)
            return self.PALETTE[self._assignments[anchor]]

        # New assignment
        if not self._available_indices:
            raise ValueError(
                f"No colors available. Remove a probe before adding new ones. "
                f"(Max probes: {len(self.PALETTE)})"
            )

        color_index = self._available_indices.pop()
        self._assignments[anchor] = color_index
        return self.PALETTE[color_index]

    def release_color(self, anchor: ProbeAnchor) -> None:
        """Release color when probe is removed, making it available for reuse."""
        if anchor in self._assignments:
            color_index = self._assignments.pop(anchor)
            # Return to available pool
            self._available_indices.append(color_index)

    def get_emphasis_level(self, anchor: ProbeAnchor) -> float:
        """
        Get emphasis level based on recency (LRU position).

        Returns:
            0.6 for oldest, 1.0 for newest, linear interpolation between
        """
        if anchor not in self._assignments:
            return 0.6

        # Get position in order (0 = oldest, n-1 = newest)
        keys = list(self._assignments.keys())
        try:
            position = keys.index(anchor)
        except ValueError:
            return 0.6

        n = len(keys)
        if n <= 1:
            return 1.0

        # Linear from 0.6 (oldest) to 1.0 (newest)
        return 0.6 + (0.4 * position / (n - 1))

    def get_deemphasized_color(self, anchor: ProbeAnchor) -> QColor:
        """
        Get color with emphasis-adjusted alpha.

        Returns color with alpha set based on recency.
        """
        if anchor not in self._assignments:
            return QColor('#666666')

        color = QColor(self.PALETTE[self._assignments[anchor]])
        emphasis = self.get_emphasis_level(anchor)
        color.setAlphaF(emphasis)
        return color

    def has_color(self, anchor: ProbeAnchor) -> bool:
        """Check if anchor has an assigned color."""
        return anchor in self._assignments

    def is_full(self) -> bool:
        """Check if all colors are assigned."""
        return len(self._available_indices) == 0

    @property
    def available_count(self) -> int:
        """Number of available color slots."""
        return len(self._available_indices)

    @property
    def assigned_count(self) -> int:
        """Number of assigned colors."""
        return len(self._assignments)
