# Plan 0: Foundation Stubs

**Focus:** Define shared interfaces and dataclasses that all other plans depend on.

**Branch:** `m1/foundation`

**Dependencies:** None (this is the foundation)

**Complexity:** Small (S)

---

## Files to Create

### `pyprobe/core/anchor.py`
```python
"""Probe anchor - immutable identity for a probe location."""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ProbeAnchor:
    """Immutable identity for a probe location in source code.

    Frozen for hashability - can be used as dict key.
    """
    file: str       # Absolute path
    line: int       # 1-indexed line number
    col: int        # Column offset (0-indexed)
    symbol: str     # Variable name at that location
    func: str = ""  # Enclosing function name (optional)

    def identity_label(self) -> str:
        """Return human-readable identity: 'symbol @ file:line'"""
        filename = self.file.split('/')[-1]  # Just filename, not full path
        return f"{self.symbol} @ {filename}:{self.line}"

    def short_label(self) -> str:
        """Return short label: 'symbol:line'"""
        return f"{self.symbol}:{self.line}"

    def to_dict(self) -> dict:
        """Convert to dict for IPC serialization."""
        return {
            'file': self.file,
            'line': self.line,
            'col': self.col,
            'symbol': self.symbol,
            'func': self.func,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'ProbeAnchor':
        """Create from dict (IPC deserialization)."""
        return cls(
            file=d['file'],
            line=d['line'],
            col=d['col'],
            symbol=d['symbol'],
            func=d.get('func', ''),
        )
```

### `pyprobe/gui/probe_state.py`
```python
"""Probe lifecycle states."""
from enum import Enum, auto

class ProbeState(Enum):
    """Visual state of a probe in the UI."""
    ARMED = auto()      # Probe created, waiting for first data
    LIVE = auto()       # Receiving data updates
    STALE = auto()      # No recent updates (> 2 seconds)
    INVALID = auto()    # Anchor no longer valid (file changed)
```

### `pyprobe/gui/probe_registry.py` (stub)
```python
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
```

### `pyprobe/gui/color_manager.py` (stub)
```python
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
```

---

## Files to Modify

### `pyprobe/ipc/messages.py` (APPEND ONLY)

Add to `MessageType` enum:
```python
# M1: Anchor-based probe commands
CMD_ADD_PROBE = auto()      # Add probe by anchor
CMD_REMOVE_PROBE = auto()   # Remove probe by anchor
DATA_PROBE_VALUE = auto()   # Probe data with anchor context
```

Add factory functions:
```python
def make_add_probe_cmd(anchor: 'ProbeAnchor', throttle_ms: float = 50.0) -> Message:
    """Create CMD_ADD_PROBE message."""
    return Message(
        msg_type=MessageType.CMD_ADD_PROBE,
        payload={
            'anchor': anchor.to_dict(),
            'throttle_ms': throttle_ms,
        }
    )

def make_remove_probe_cmd(anchor: 'ProbeAnchor') -> Message:
    """Create CMD_REMOVE_PROBE message."""
    return Message(
        msg_type=MessageType.CMD_REMOVE_PROBE,
        payload={'anchor': anchor.to_dict()}
    )

def make_probe_value_msg(
    anchor: 'ProbeAnchor',
    value: Any,
    dtype: str,
    shape: Optional[tuple] = None,
) -> Message:
    """Create DATA_PROBE_VALUE message."""
    return Message(
        msg_type=MessageType.DATA_PROBE_VALUE,
        payload={
            'anchor': anchor.to_dict(),
            'value': value,
            'dtype': dtype,
            'shape': shape,
        }
    )
```

---

## Verification

```bash
python -c "from pyprobe.core.anchor import ProbeAnchor; a = ProbeAnchor('/test.py', 10, 4, 'x', 'foo'); print(a.identity_label())"
# Should print: x @ test.py:10
```

---

## Merge Conflict Risk

**Low** - Only appends to `messages.py` enum and adds new files.
