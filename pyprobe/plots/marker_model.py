from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Union, Tuple, List
from PyQt6.QtCore import QObject, pyqtSignal


class _StoreSignals(QObject):
    """Module-level signals for MarkerStore lifecycle events."""
    stores_changed = pyqtSignal()
    marker_content_changed = pyqtSignal()

_store_signals = _StoreSignals()

class MarkerType(Enum):
    ABSOLUTE = auto()
    RELATIVE = auto()

class MarkerShape(Enum):
    DIAMOND = auto()
    TRIANGLE_UP = auto()
    SQUARE = auto()
    CROSS = auto()
    CIRCLE = auto()
    STAR = auto()

MARKER_COLORS = [
    '#CC3333',   # red      — visible on dark and light backgrounds
    '#2E9E4F',   # green
    '#3355CC',   # blue
    '#B07D00',   # amber    — replaces yellow (near-invisible on white)
    '#9B33B0',   # purple   — replaces magenta
    '#1A8FA0',   # teal     — replaces cyan (near-invisible on white)
    '#CC6F1A',   # orange
    '#5C8A00',   # olive-green
    '#1A6FCC',   # cornflower blue
    '#B03375',   # raspberry
]

@dataclass
class MarkerData:
    id: str
    x: float
    y: float
    trace_key: Union[int, str]
    marker_type: MarkerType = MarkerType.ABSOLUTE
    ref_marker_id: Optional[str] = None
    label: str = None
    shape: MarkerShape = None
    color: str = MARKER_COLORS[0]

    def __post_init__(self):
        if self.label is None:
            self.label = self.id
        if self.shape is None:
            # Auto-cycle from id index, e.g. "m0" -> 0
            try:
                idx = int(self.id[1:])
                shapes = list(MarkerShape)
                self.shape = shapes[idx % len(shapes)]
            except (ValueError, IndexError):
                self.shape = MarkerShape.DIAMOND

class MarkerStore(QObject):
    markers_changed = pyqtSignal()

    _global_used_ids: set = set()
    _all_stores: list = []

    @classmethod
    def all_stores(cls) -> list:
        """Return list of live MarkerStore instances, pruning deleted ones."""
        live = []
        for s in list(cls._all_stores):
            try:
                s.objectName()  # test if Qt object is alive
                live.append(s)
            except RuntimeError:
                pass
        cls._all_stores = live
        return live

    @classmethod
    def store_signals(cls) -> _StoreSignals:
        """Access the module-level lifecycle signals."""
        return _store_signals

    def __init__(self, parent=None):
        super().__init__(parent)
        self._markers: dict[str, MarkerData] = {}
        MarkerStore._all_stores.append(self)
        _store_signals.stores_changed.emit()

    def dispose(self, release_ids: bool = True):
        """Release all IDs owned by this store from the global set. Call before discarding."""
        if release_ids:
            for m_id in list(self._markers.keys()):
                MarkerStore._global_used_ids.discard(m_id)
        self._markers.clear()
        if self in MarkerStore._all_stores:
            MarkerStore._all_stores.remove(self)
        _store_signals.stores_changed.emit()

    def add_marker_data(self, data: MarkerData):
        """Add an existing MarkerData object (e.g., from persistence)."""
        self._markers[data.id] = data
        MarkerStore._global_used_ids.add(data.id)
        self.markers_changed.emit()

    def add_marker(self, trace_key: Union[int, str], x: float, y: float, color: str = MARKER_COLORS[0]) -> MarkerData:
        m_id = self.get_next_id()
        # Auto-assign color from palette when caller doesn't specify one
        if color == MARKER_COLORS[0]:
            try:
                idx = int(m_id[1:])
            except (ValueError, IndexError):
                idx = 0
            color = MARKER_COLORS[idx % len(MARKER_COLORS)]
        data = MarkerData(id=m_id, x=x, y=y, trace_key=trace_key, color=color)
        self._markers[m_id] = data
        self.markers_changed.emit()
        _store_signals.marker_content_changed.emit()
        return data

    def remove_marker(self, marker_id: str):
        if marker_id in self._markers:
            # Clear ref for dependent markers
            for m in self._markers.values():
                if m.ref_marker_id == marker_id:
                    m.marker_type = MarkerType.ABSOLUTE
                    m.ref_marker_id = None

            del self._markers[marker_id]
            MarkerStore._global_used_ids.discard(marker_id)
            self.markers_changed.emit()
            _store_signals.marker_content_changed.emit()

    def update_marker(self, marker_id: str, **kwargs):
        if marker_id not in self._markers:
            return

        m = self._markers[marker_id]

        old_x = m.x

        for k, v in kwargs.items():
            if hasattr(m, k):
                setattr(m, k, v)

        # If x changed, update downstream relative markers
        if 'x' in kwargs:
            dx = m.x - old_x
            if dx != 0:
                for dep in self._markers.values():
                    if dep.marker_type == MarkerType.RELATIVE and dep.ref_marker_id == marker_id:
                        dep.x += dx

        self.markers_changed.emit()
        _store_signals.marker_content_changed.emit()

    def clear_markers(self) -> None:
        """Remove all markers."""
        if not self._markers:
            return
        for m_id in self._markers:
            MarkerStore._global_used_ids.discard(m_id)
        self._markers.clear()
        self.markers_changed.emit()
        _store_signals.marker_content_changed.emit()

    def get_markers(self) -> List[MarkerData]:
        return list(self._markers.values())

    def get_marker(self, marker_id: str) -> Optional[MarkerData]:
        return self._markers.get(marker_id)

    def get_next_id(self) -> str:
        """Find the lowest m{i} not used by any MarkerStore globally."""
        i = 0
        while True:
            m_id = f"m{i}"
            if m_id not in MarkerStore._global_used_ids:
                MarkerStore._global_used_ids.add(m_id)
                return m_id
            i += 1

    def get_display_values(self, marker_id: str) -> Tuple[float, float]:
        m = self._markers.get(marker_id)
        if not m:
            return (0.0, 0.0)

        if m.marker_type == MarkerType.RELATIVE and m.ref_marker_id and m.ref_marker_id in self._markers:
            ref = self._markers[m.ref_marker_id]
            return (m.x - ref.x, m.y - ref.y)

        return (m.x, m.y)
