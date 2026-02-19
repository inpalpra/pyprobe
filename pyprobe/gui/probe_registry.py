"""Probe registry - central management of all probes with liveness tracking."""
from typing import Dict, Set, Optional
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QColor

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.gui.probe_state import ProbeState
from pyprobe.gui.color_manager import ColorManager


class ProbeRegistry(QObject):
    """
    Central registry for all active probes.

    Manages:
    - Probe lifecycle (add, remove, invalidate)
    - Color assignments via ColorManager
    - Liveness tracking (ARMED -> LIVE -> STALE transitions)
    - Signals for UI updates
    """

    # Timing constants
    STALE_TIMEOUT_MS = 2000  # 2 seconds without data -> STALE
    STALE_CHECK_INTERVAL_MS = 500  # Check every 500ms

    # Signals
    probe_added = pyqtSignal(object, object)          # (anchor, color)
    probe_removed = pyqtSignal(object)                # (anchor,)
    probe_state_changed = pyqtSignal(object, object)  # (anchor, state)
    probe_invalidated = pyqtSignal(object)            # (anchor,)

    def __init__(self, parent=None):
        super().__init__(parent)

        # State tracking
        self._probes: Dict[ProbeAnchor, ProbeState] = {}
        self._last_data_time: Dict[ProbeAnchor, float] = {}

        # Color management
        self._color_manager = ColorManager()

        # Stale detection timer
        self._stale_timer = QTimer(self)
        self._stale_timer.timeout.connect(self._check_stale)
        self._stale_timer.start(self.STALE_CHECK_INTERVAL_MS)

        # Track current time for liveness (updated externally or via QTimer)
        self._current_time_ms = 0

    def add_probe(self, anchor: ProbeAnchor) -> QColor:
        """
        Add a new probe and return its assigned color.

        Probe starts in ARMED state, waiting for first data.

        Args:
            anchor: The probe anchor identifying the code location

        Returns:
            QColor assigned to this probe

        Raises:
            ValueError: If no colors available
        """
        if anchor in self._probes:
            # Already exists - just return color
            return self._color_manager.get_color(anchor)

        # Get color from manager (may raise ValueError if full)
        color = self._color_manager.get_color(anchor)

        # Initialize state
        self._probes[anchor] = ProbeState.ARMED
        self._last_data_time[anchor] = self._current_time_ms

        # Emit signal
        self.probe_added.emit(anchor, color)

        return color

    def remove_probe(self, anchor: ProbeAnchor) -> None:
        """Remove a probe and release its color."""
        if anchor not in self._probes:
            return

        # Clean up state
        del self._probes[anchor]
        self._last_data_time.pop(anchor, None)

        # Release color for reuse
        self._color_manager.release_color(anchor)

        # Emit signal
        self.probe_removed.emit(anchor)

    def update_data_received(self, anchor: ProbeAnchor) -> None:
        """
        Update liveness when data is received.

        Transitions ARMED -> LIVE or refreshes STALE -> LIVE.
        """
        if anchor not in self._probes:
            return

        # Update timestamp
        self._last_data_time[anchor] = self._current_time_ms

        # Update state if needed
        old_state = self._probes[anchor]
        if old_state in (ProbeState.ARMED, ProbeState.STALE):
            self._probes[anchor] = ProbeState.LIVE
            self.probe_state_changed.emit(anchor, ProbeState.LIVE)

    def invalidate_anchor(self, anchor: ProbeAnchor) -> None:
        """Mark a single anchor as invalid (source file changed)."""
        if anchor not in self._probes:
            return

        old_state = self._probes[anchor]
        if old_state != ProbeState.INVALID:
            self._probes[anchor] = ProbeState.INVALID
            self.probe_state_changed.emit(anchor, ProbeState.INVALID)
            self.probe_invalidated.emit(anchor)

    def invalidate_anchors(self, anchors: Set[ProbeAnchor]) -> None:
        """Mark multiple anchors as invalid."""
        for anchor in anchors:
            self.invalidate_anchor(anchor)

    def get_color(self, anchor: ProbeAnchor) -> Optional[QColor]:
        """Get the assigned color for an anchor."""
        if anchor in self._probes:
            return self._color_manager.get_color(anchor)
        return None

    def get_state(self, anchor: ProbeAnchor) -> Optional[ProbeState]:
        """Get probe state."""
        return self._probes.get(anchor)

    def set_current_time(self, time_ms: float) -> None:
        """Update current time for liveness tracking."""
        self._current_time_ms = time_ms

    def _check_stale(self) -> None:
        """Timer callback to detect and transition stale probes."""
        import time
        self._current_time_ms = time.time() * 1000

        for anchor, state in list(self._probes.items()):
            # Only check LIVE probes for staleness
            if state != ProbeState.LIVE:
                continue

            last_time = self._last_data_time.get(anchor, 0)
            if self._current_time_ms - last_time > self.STALE_TIMEOUT_MS:
                self._probes[anchor] = ProbeState.STALE
                self.probe_state_changed.emit(anchor, ProbeState.STALE)

    @property
    def active_anchors(self) -> Set[ProbeAnchor]:
        """Return set of all active (non-invalid) anchors."""
        return {
            anchor for anchor, state in self._probes.items()
            if state != ProbeState.INVALID
        }

    @property
    def all_anchors(self) -> Set[ProbeAnchor]:
        """Return set of all anchors (including invalid)."""
        return set(self._probes.keys())

    @property
    def color_manager(self) -> ColorManager:
        """Access to color manager for advanced operations."""
        return self._color_manager

    def is_full(self) -> bool:
        """Check if registry is at capacity (no colors available)."""
        return self._color_manager.is_full()

    def clear(self) -> None:
        """Remove all probes and release all colors."""
        for anchor in list(self._probes.keys()):
            self.remove_probe(anchor)
