"""Efficient anchor matching for trace function."""
from typing import Dict, List, Optional, Set, Tuple
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.logging import trace_print

class AnchorMatcher:
    """Index structure for O(1) anchor lookup in trace function.

    Indexed by (file, line) for fast filtering in hot path.
    """

    def __init__(self):
        self._by_location: Dict[Tuple[str, int], List[ProbeAnchor]] = {}
        self._all_anchors: Set[ProbeAnchor] = set()

    def add(self, anchor: ProbeAnchor) -> None:
        """Add anchor to index."""
        key = (anchor.file, anchor.line)
        if key not in self._by_location:
            self._by_location[key] = []
        if anchor not in self._all_anchors:
            self._by_location[key].append(anchor)
            self._all_anchors.add(anchor)

    def remove(self, anchor: ProbeAnchor) -> None:
        """Remove anchor from index."""
        key = (anchor.file, anchor.line)
        if key in self._by_location:
            try:
                self._by_location[key].remove(anchor)
                if not self._by_location[key]:
                    del self._by_location[key]
            except ValueError:
                pass
        self._all_anchors.discard(anchor)

    def match(self, file: str, line: int, local_vars: Set[str]) -> List[ProbeAnchor]:
        """Find all matching anchors for a (file, line) with given local variables."""
        key = (file, line)
        candidates = self._by_location.get(key, [])
        # Debug: print candidates and their is_assignment status
        if candidates:
            trace_print(f"AnchorMatcher.match: line={line}, candidates={[(a.symbol, getattr(a, 'is_assignment', False)) for a in candidates]}")
        # Include if symbol is in locals OR if it's an assignment target (will be deferred)
        result = [
            a for a in candidates 
            if a.symbol in local_vars or getattr(a, 'is_assignment', False)
        ]
        if candidates:
            trace_print(f"AnchorMatcher.match: matched={[a.symbol for a in result]}")
        return result

    def has_file(self, file: str) -> bool:
        """Check if any anchors exist for this file."""
        return any(f == file for f, _ in self._by_location.keys())

    def has_location(self, file: str, line: int) -> bool:
        """Check if any anchors exist at this location."""
        return (file, line) in self._by_location

    @property
    def files(self) -> Set[str]:
        return {f for f, _ in self._by_location.keys()}

    @property
    def all_anchors(self) -> Set[ProbeAnchor]:
        return self._all_anchors.copy()

    def clear(self) -> None:
        self._by_location.clear()
        self._all_anchors.clear()
