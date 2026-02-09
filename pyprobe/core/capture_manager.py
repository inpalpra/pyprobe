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
        old_object_id: Optional[int] = None,
    ) -> int:
        """Reserve a sequence number for a deferred (LHS) capture.
        
        Args:
            old_object_id: If provided, flush will only happen when the 
                           object ID of the variable changes (detecting new assignment).
        """
        ts = self._clock() if timestamp is None else timestamp
        seq_num = self._seq_gen.next()
        pending = self._pending.setdefault(frame_id, [])
        pending.append(
            _DeferredItem(
                anchor=anchor,
                seq_num=seq_num,
                timestamp=ts,
                logical_order=logical_order,
                old_object_id=old_object_id,
            )
        )
        trace_print(f"DEFER: {anchor.symbol}@{anchor.line} (LHS, old_id={old_object_id})")
        return seq_num

    def flush_deferred(
        self,
        frame_id: int,
        event: str,
        resolve_value: Callable[[ProbeAnchor], Tuple[object, str, Optional[tuple]]],
        get_object_id: Optional[Callable[[ProbeAnchor], Optional[int]]] = None,
    ) -> List[CaptureRecord]:
        """Flush deferred captures on line/return/exception events.
        
        Args:
            get_object_id: If provided, returns the current object ID for an anchor.
                          Used to detect if a new assignment has occurred.
        """
        if event not in ("line", "return", "exception"):
            return []

        pending = self._pending.get(frame_id)
        if not pending:
            return []
        
        records: List[CaptureRecord] = []
        still_pending: List[_DeferredItem] = []

        for item in pending:
            # Check if object ID has changed (indicating new assignment)
            if item.old_object_id is not None and get_object_id is not None:
                try:
                    current_id = get_object_id(item.anchor)
                    if current_id == item.old_object_id:
                        # Still has old value - assignment hasn't completed yet
                        if event == "line":
                            still_pending.append(item)
                            trace_print(f"SKIP: {item.anchor.symbol}@{item.anchor.line} (same object id={current_id}, waiting for new assignment)")
                        continue
                except KeyError:
                    if event == "line":
                        still_pending.append(item)
                    continue
            
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
            trace_print(f"FLUSH: {item.anchor.symbol}@{item.anchor.line} dtype={dtype}")

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
    old_object_id: Optional[int] = None  # Track object ID to detect new assignment
