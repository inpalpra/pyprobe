"""Redraw throttling for probe buffers."""

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from ..core.anchor import ProbeAnchor
from ..core.capture_record import CaptureRecord
from .probe_buffer import ProbeDataBuffer


@dataclass
class RedrawThrottler:
    """Throttle redraws while always storing incoming captures."""

    min_interval_ms: float = 16.0
    clock: Callable[[], float] = time.perf_counter
    _buffers: Dict[ProbeAnchor, ProbeDataBuffer] = field(default_factory=dict, init=False)
    _dirty: Dict[ProbeAnchor, ProbeDataBuffer] = field(default_factory=dict, init=False)
    _last_redraw: float = field(default=0.0, init=False)

    def receive(self, record: CaptureRecord) -> None:
        """Store a capture record and mark its buffer as dirty."""
        buffer = self._buffers.get(record.anchor)
        if buffer is None:
            buffer = ProbeDataBuffer(anchor=record.anchor)
            self._buffers[record.anchor] = buffer
        buffer.append(record)
        self._dirty[record.anchor] = buffer

    def should_redraw(self) -> bool:
        """Return True if enough time elapsed since last redraw."""
        now = self.clock()
        if now - self._last_redraw >= self.min_interval_ms / 1000.0:
            self._last_redraw = now
            return True
        return False

    def get_dirty_buffers(self) -> Dict[ProbeAnchor, ProbeDataBuffer]:
        """Return and clear buffers that received new data."""
        dirty = dict(self._dirty)
        self._dirty.clear()
        return dirty

    def buffer_for(self, anchor: ProbeAnchor) -> Optional[ProbeDataBuffer]:
        """Get the buffer for a probe anchor if present."""
        return self._buffers.get(anchor)

    @property
    def buffer_count(self) -> int:
        """Number of buffers tracked."""
        return len(self._buffers)
