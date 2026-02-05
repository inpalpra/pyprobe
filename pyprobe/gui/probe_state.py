"""Probe lifecycle states."""
from enum import Enum, auto


class ProbeState(Enum):
    """Visual state of a probe in the UI."""
    ARMED = auto()      # Probe created, waiting for first data
    LIVE = auto()       # Receiving data updates
    STALE = auto()      # No recent updates (> 2 seconds)
    INVALID = auto()    # Anchor no longer valid (file changed)
