"""
Deferred Capture Manager - handles delayed capture of assignment targets.

When a probe is placed on an assignment target (LHS of `=`), we can't capture
the value immediately because the assignment hasn't executed yet. Instead, we:
1. Defer the capture when we first see the assignment line
2. Flush (actually capture) on the next line after the assignment completes
"""

import time
from typing import Dict, List, Tuple, Any, Optional, Callable
import numpy as np

from .anchor import ProbeAnchor
from .data_classifier import classify_data
from pyprobe.logging import trace_print


class DeferredCaptureManager:
    """
    Manages delayed capture of assignment targets.
    
    Design: When we encounter an assignment target, we record:
    - The anchor (probe definition)
    - The line number where we saw it
    - The object ID of the current value (or None if variable doesn't exist)
    
    On the next line event (different line), we check if a new assignment
    happened by comparing object IDs. If so, we capture the new value.
    """
    
    def __init__(self):
        # frame_id -> [(anchor, deferred_line, old_object_id), ...]
        self._pending: Dict[int, List[Tuple[ProbeAnchor, int, Optional[int]]]] = {}
    
    def defer(
        self,
        frame_id: int,
        anchor: ProbeAnchor,
        line: int,
        old_id: Optional[int]
    ) -> None:
        """
        Register a deferred capture for an assignment target.
        
        Args:
            frame_id: id(frame) to track per-frame pending list
            anchor: The probe anchor to capture
            line: The line number where the assignment is
            old_id: id() of current value, or None if variable doesn't exist yet
        """
        if frame_id not in self._pending:
            self._pending[frame_id] = []
        trace_print(f"DEFER: {anchor.symbol} at anchor.line={anchor.line}, frame_line={line}, old_id={old_id}")
        self._pending[frame_id].append((anchor, line, old_id))
    
    def has_pending(self, frame_id: int) -> bool:
        """Check if there are pending deferred captures for this frame."""
        return frame_id in self._pending and len(self._pending[frame_id]) > 0
    
    def flush(
        self,
        frame,
        event: str,
        create_capture_fn: Callable[[ProbeAnchor, Any, float], Any]
    ) -> List[Tuple[ProbeAnchor, Any]]:
        """
        Process pending deferred captures and return those ready to emit.
        
        Only flushes captures when:
        1. Event is 'line' (a new statement is starting)
        2. We're on a DIFFERENT line than where they were deferred
        3. The variable exists AND has a different object ID (assignment happened)
        
        Args:
            frame: The current stack frame
            event: The trace event type ('line', 'return', 'call', 'exception')
            create_capture_fn: Function(anchor, value, timestamp) -> CapturedVariable
            
        Returns:
            List of (anchor, captured_variable) tuples ready to send
        """
        # Flush on 'line' events (normal case) and 'return' events (end of function)
        # 'return' is critical to capture deferred assignments at the end of loops
        # where there's no subsequent 'line' event before the frame disappears
        if event not in ('line', 'return'):
            return []
        
        frame_id = id(frame)
        pending = self._pending.get(frame_id)
        if not pending:
            return []
        
        current_line = frame.f_lineno
        
        # Separate into ready-to-flush (different line + var exists + ID changed)
        # vs still pending
        ready_to_flush = []
        still_pending = []
        
        for anchor, original_line, old_id in pending:
            trace_print(f"_flush_deferred: anchor={anchor.symbol}, original_line={original_line}, current_line={current_line}")
            
            # CRITICAL: Only flush if we're on a DIFFERENT line than where registered
            if current_line == original_line:
                trace_print(f"_flush_deferred: Same line, keeping pending")
                still_pending.append((anchor, original_line, old_id))
                continue
            
            # We're on a different line - check if variable now exists AND has a new ID
            symbol = anchor.symbol
            if symbol in frame.f_locals:
                current_id = id(frame.f_locals[symbol])
            elif symbol in frame.f_globals:
                current_id = id(frame.f_globals[symbol])
            else:
                # Variable doesn't exist yet
                still_pending.append((anchor, original_line, old_id))
                continue
            
            # Only flush if the object ID has changed (meaning a new assignment happened)
            if current_id != old_id:
                ready_to_flush.append(anchor)
            else:
                trace_print(f"_flush_deferred: Same object ID, keeping pending")
                still_pending.append((anchor, original_line, old_id))
        
        # Update pending list
        if still_pending:
            self._pending[frame_id] = still_pending
        else:
            self._pending.pop(frame_id, None)
        
        if not ready_to_flush:
            return []
        
        # Capture them using current state
        current_time = time.perf_counter()
        batch = []
        
        for anchor in ready_to_flush:
            try:
                # Value should now be available (post-execution of the ORIGINAL line)
                if anchor.symbol in frame.f_locals:
                    value = frame.f_locals[anchor.symbol]
                else:
                    value = frame.f_globals[anchor.symbol]
                
                # Debug trace for complex arrays
                if isinstance(value, np.ndarray) and np.iscomplexobj(value):
                    trace_print(f"_flush_deferred CAPTURE: {anchor.symbol} at line {anchor.line}, current_line={current_line}, mean={value.mean():.4f}")
                
                captured = create_capture_fn(anchor, value, current_time)
                batch.append((anchor, captured))
            except KeyError:
                continue
            except Exception:
                continue
        
        return batch
