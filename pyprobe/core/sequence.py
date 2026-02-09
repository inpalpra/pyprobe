"""Thread-safe monotonic sequence generator."""

import threading


class SequenceGenerator:
    """Generates monotonically increasing integers."""

    def __init__(self, start: int = 0) -> None:
        self._lock = threading.Lock()
        self._next = start

    def next(self) -> int:
        """Return the next sequence number."""
        with self._lock:
            current = self._next
            self._next += 1
            return current
