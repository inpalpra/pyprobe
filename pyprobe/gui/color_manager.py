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
    """

    # Generate 100 colors from HSL color wheel (high saturation, varied hue)
    MAX_PROBES = 100
    
    @staticmethod
    def _generate_palette(count: int) -> list[QColor]:
        """Generate a palette of distinct colors using HSL."""
        colors = []
        for i in range(count):
            # Spread hues evenly, use golden ratio for better distribution
            hue = (i * 137.508) % 360  # Golden angle in degrees
            saturation = 0.85  # High saturation for visibility
            lightness = 0.55   # Medium lightness for dark backgrounds
            color = QColor.fromHslF(hue / 360.0, saturation, lightness)
            colors.append(color)
        return colors

    def __init__(self):
        # Per-instance palette so appends in update_color/reserve_color
        # don't leak across instances (important for test isolation).
        self.PALETTE = self._generate_palette(self.MAX_PROBES)
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

    def update_color(self, anchor: ProbeAnchor, color: QColor) -> None:
        """
        Update or assign a specific color to an anchor.
        This allows user-initiated overrides that should persist across all widgets.
        """
        # If it matches an existing palette color exactly, we try to use its index
        color_hex = color.name().lower()
        matched_index = -1
        for i, p_color in enumerate(self.PALETTE):
            if p_color.name().lower() == color_hex:
                matched_index = i
                break

        if matched_index >= 0:
            # If it's already assigned to this anchor, just move to end
            if anchor in self._assignments and self._assignments[anchor] == matched_index:
                self._assignments.move_to_end(anchor)
                return
            
            # If it was assigned to someone else, we don't care, we'll just share the index
            # for this user-specified override.
            if anchor in self._assignments:
                # If we were holding an index, we don't necessarily release it if it's 
                # still being used by the palette (recycling logic is complex),
                # but for simplicity we'll just update our pointer.
                pass
            
            self._assignments[anchor] = matched_index
            self._assignments.move_to_end(anchor)
        else:
            # Custom color not in palette - add it
            new_idx = len(self.PALETTE)
            self.PALETTE.append(color)
            self._assignments[anchor] = new_idx
            self._assignments.move_to_end(anchor)

    def reserve_color(self, anchor: ProbeAnchor, color: QColor) -> None:
        """
        Manually assign a specific color to an anchor, useful when loading saved presets.
        Tries to match it with the standard palette to remove it from the pool.
        """
        if anchor in self._assignments:
            self._assignments.move_to_end(anchor)
            return

        # Find if this exact color string exists in the palette pool
        color_hex = color.name().lower()
        matched_index = -1
        for idx in self._available_indices:
            if self.PALETTE[idx].name().lower() == color_hex:
                matched_index = idx
                break
                
        if matched_index >= 0:
            # We found it in the pool, reserve it properly
            self._available_indices.remove(matched_index)
            self._assignments[anchor] = matched_index
        else:
            # Color is either custom or already assigned to someone else.
            # We'll just append this new custom color to the end of the palette
            # and act like it's a standard one.
            new_idx = len(self.PALETTE)
            self.PALETTE.append(color)
            self._assignments[anchor] = new_idx

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
