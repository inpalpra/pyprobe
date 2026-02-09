"""Capture record data structure for ordered probe captures."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .anchor import ProbeAnchor


@dataclass(frozen=True)
class CaptureRecord:
    """Capture record with ordering metadata."""

    anchor: ProbeAnchor
    value: Any
    dtype: str
    shape: Optional[tuple]
    seq_num: int
    timestamp: int
    logical_order: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for IPC or persistence."""
        return {
            'anchor': self.anchor.to_dict(),
            'value': self.value,
            'dtype': self.dtype,
            'shape': self.shape,
            'seq_num': self.seq_num,
            'timestamp': self.timestamp,
            'logical_order': self.logical_order,
        }

    @staticmethod
    def from_dict(payload: Dict[str, Any]) -> "CaptureRecord":
        """Deserialize from IPC payload."""
        return CaptureRecord(
            anchor=ProbeAnchor.from_dict(payload['anchor']),
            value=payload.get('value'),
            dtype=payload.get('dtype', 'unknown'),
            shape=payload.get('shape'),
            seq_num=payload.get('seq_num', -1),
            timestamp=payload.get('timestamp', 0),
            logical_order=payload.get('logical_order', 0),
        )
