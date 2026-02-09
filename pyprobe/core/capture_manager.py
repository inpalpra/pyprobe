"""Capture orchestration for ordered probe captures."""

import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .anchor import ProbeAnchor
from .capture_record import CaptureRecord
from .sequence import SequenceGenerator
from pyprobe.logging import trace_print


class CaptureManager:
    """Create ordered CaptureRecords for immediate captures."""

    def __init__(
        self,
        seq_gen: Optional[SequenceGenerator] = None,
        clock: Optional[Callable[[], int]] = None,
    ) -> None:
        self._seq_gen = seq_gen or SequenceGenerator()
        self._clock = clock or time.perf_counter_ns
        self._pending: Dict[int, List[_DeferredItem]] = {}

    def capture_immediate(
        self,
        anchor: ProbeAnchor,
        value,
        dtype: str,
        shape: Optional[tuple],
        timestamp: Optional[int] = None,
        logical_order: int = 0,
    ) -> CaptureRecord:
        """Capture an immediate RHS value."""
        seq_num = self._seq_gen.next()
        ts = self._clock() if timestamp is None else timestamp
        return CaptureRecord(
            anchor=anchor,
            value=value,
            dtype=dtype,
            shape=shape,
            seq_num=seq_num,
            timestamp=ts,
            logical_order=logical_order,
        )

    def capture_batch(
        self,
        items: Sequence[Tuple[ProbeAnchor, object, str, Optional[tuple]]],
        timestamp: Optional[int] = None,
    ) -> List[CaptureRecord]:
        """Capture a batch of RHS values from the same trace event."""
        ts = self._clock() if timestamp is None else timestamp
        records: List[CaptureRecord] = []
        for logical_order, (anchor, value, dtype, shape) in enumerate(items):
            records.append(
                self.capture_immediate(
                    anchor=anchor,
                    value=value,
                    dtype=dtype,
                    shape=shape,
                    timestamp=ts,
                    logical_order=logical_order,
                )
            )
        return records

    def defer_capture(
        self,
        frame_id: int,
        anchor: ProbeAnchor,
        logical_order: int = 0,
        timestamp: Optional[int] = None,
    ) -> int:
        """Reserve a sequence number for a deferred (LHS) capture."""
        ts = self._clock() if timestamp is None else timestamp
        seq_num = self._seq_gen.next()
        pending = self._pending.setdefault(frame_id, [])
        pending.append(
            _DeferredItem(
                anchor=anchor,
                seq_num=seq_num,
                timestamp=ts,
                logical_order=logical_order,
            )
        )
        trace_print(f"DEBUG: Deferred capture for {anchor.symbol} at {anchor.line}. Seq={seq_num}, frame={frame_id}")
        return seq_num

    def flush_deferred(
        self,
        frame_id: int,
        event: str,
        resolve_value: Callable[[ProbeAnchor], Tuple[object, str, Optional[tuple]]],
    ) -> List[CaptureRecord]:
        """Flush deferred captures on line/return/exception events."""
        if event not in ("line", "return", "exception"):
            return []

        pending = self._pending.get(frame_id)
        if not pending:
            return []
        
        records: List[CaptureRecord] = []
        still_pending: List[_DeferredItem] = []

        for item in pending:
            try:
                value, dtype, shape = resolve_value(item.anchor)
            except KeyError:
                if event == "line":
                    still_pending.append(item)
                continue

            records.append(
                CaptureRecord(
                    anchor=item.anchor,
                    value=value,
                    dtype=dtype,
                    shape=shape,
                    seq_num=item.seq_num,
                    timestamp=item.timestamp,
                    logical_order=item.logical_order,
                )
            )

        if still_pending:
            self._pending[frame_id] = still_pending
        else:
            self._pending.pop(frame_id, None)

        return records

    def has_pending(self, frame_id: int) -> bool:
        """Check if a frame has pending deferred captures."""
        pending = self._pending.get(frame_id)
        return bool(pending)


@dataclass(frozen=True)
class _DeferredItem:
    anchor: ProbeAnchor
    seq_num: int
    timestamp: int
    logical_order: int
