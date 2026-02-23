"""
The heart of PyProbe - implements variable interception via sys.settrace
with careful attention to minimizing overhead in tight loops.
"""

import sys
import time
from typing import Dict, List, Set, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import numpy as np

from .data_classifier import (
    classify_data, get_waveform_info, get_waveform_collection_info,
    get_array_collection_info,
    DTYPE_WAVEFORM_REAL, DTYPE_WAVEFORM_COMPLEX,
    DTYPE_WAVEFORM_COLLECTION, DTYPE_ARRAY_COLLECTION
)
from .anchor import ProbeAnchor
from .anchor_matcher import AnchorMatcher
from .capture_manager import CaptureManager
from .capture_record import CaptureRecord
from pyprobe.logging import trace_print


class ThrottleStrategy(Enum):
    """Rate limiting strategies for different use cases."""
    NONE = auto()           # No throttling (dangerous for tight loops)
    TIME_BASED = auto()     # Send at most every N milliseconds
    SAMPLE_EVERY_N = auto() # Send every Nth iteration
    CHANGE_DETECT = auto()  # Only send when value changes significantly


@dataclass
class WatchConfig:
    """Configuration for a watched variable."""
    var_name: str
    throttle_strategy: ThrottleStrategy = ThrottleStrategy.TIME_BASED
    throttle_param: float = 50.0  # ms for TIME_BASED, N for SAMPLE_EVERY_N
    change_threshold: float = 0.01  # For CHANGE_DETECT: relative change threshold
    enabled: bool = True

    # Runtime state (not serialized)
    last_send_time: float = field(default=0.0, repr=False)
    iteration_count: int = field(default=0, repr=False)
    last_value_hash: Optional[int] = field(default=None, repr=False)


@dataclass
class CapturedVariable:
    """Data captured from a traced variable."""
    name: str
    value: Any  # Will be numpy array, scalar, or other
    dtype: str  # 'array_1d', 'array_complex', 'scalar', 'unknown'
    shape: Optional[tuple]
    timestamp: float
    source_file: str
    line_number: int
    function_name: str


class VariableTracer:
    """
    Implements sys.settrace-based variable interception with rate limiting.

    Design decisions for minimizing overhead:
    1. Early exit in trace function for non-watched files/functions
    2. Anchor-based matching for O(1) lookup
    """

    def __init__(
        self,
        data_callback: Callable[[CapturedVariable], None],
        target_files: Optional[Set[str]] = None,
        target_functions: Optional[Set[str]] = None,
        anchor_data_callback: Optional[Callable[[ProbeAnchor, CapturedVariable], None]] = None,
        anchor_batch_callback: Optional[Callable[[list], None]] = None,
        capture_record_callback: Optional[Callable[[CaptureRecord], None]] = None,
        capture_record_batch_callback: Optional[Callable[[List[CaptureRecord]], None]] = None,
    ):
        """
        Args:
            data_callback: Called when a variable capture passes throttling
            target_files: Only trace these files (None = all files)
            target_functions: Only trace these functions (None = all functions)
            anchor_data_callback: Called for anchor-based captures (anchor, captured_var)
            anchor_batch_callback: Called with list of (anchor, captured_var) tuples from same trace event
            capture_record_callback: Called with CaptureRecord for capture pipeline tests
            capture_record_batch_callback: Called with list of CaptureRecords from same trace event
        """
        self._data_callback = data_callback
        self._anchor_data_callback = anchor_data_callback
        self._anchor_batch_callback = anchor_batch_callback
        self._capture_record_callback = capture_record_callback
        self._capture_record_batch_callback = capture_record_batch_callback
        self._target_files = target_files
        self._target_functions = target_functions
        self._enabled = False
        self._global_throttle_ms = 16.67  # ~60 FPS max update rate

        # Paths to skip (stdlib, site-packages)
        self._skip_prefixes = (
            '<frozen',
            '<string>',
        )

        # Anchor-based watching
        self._anchor_matcher = AnchorMatcher()
        self._anchor_watches: Dict[ProbeAnchor, WatchConfig] = {}
        
        # Capture manager for ordered captures
        self._capture_manager = CaptureManager()

    def stop(self) -> None:
        """Disable tracing."""
        self._enabled = False
        sys.settrace(None)

    def _serialize_value(self, value: Any) -> Any:
        """
        Convert value to a serializable format for IPC.
        
        Handles waveform-like objects (2 scalars + 1 array) and waveform collections
        by converting to dicts that can be pickled across processes.
        """
        # Check for waveform collection first
        collection_info = get_waveform_collection_info(value)
        if collection_info is not None:
            serialized_waveforms = []
            for wf_data in collection_info['waveforms']:
                obj = wf_data['obj']
                info = wf_data['info']
                samples_attr = info['samples_attr']
                scalar_attrs = info['scalar_attrs']
                
                samples = np.asarray(getattr(obj, samples_attr)).copy()
                scalars = [float(getattr(obj, attr)) for attr in scalar_attrs]
                
                serialized_waveforms.append({
                    'samples': samples,
                    'scalars': scalars,
                })
            
            return {
                '__dtype__': DTYPE_WAVEFORM_COLLECTION,
                'waveforms': serialized_waveforms,
            }

        # Check for array collection (list/tuple of 1D real arrays)
        array_collection = get_array_collection_info(value)
        if array_collection is not None:
            return {
                '__dtype__': DTYPE_ARRAY_COLLECTION,
                'arrays': [arr.copy() for arr in array_collection['arrays']],
            }

        # Check for single waveform-like object
        waveform_info = get_waveform_info(value)
        if waveform_info is not None:
            samples_attr = waveform_info['samples_attr']
            scalar_attrs = waveform_info['scalar_attrs']
            
            samples = np.asarray(getattr(value, samples_attr)).copy()
            scalars = [float(getattr(value, attr)) for attr in scalar_attrs]
            
            # Use complex tag if the samples are complex
            is_complex = waveform_info.get('is_complex', False)
            dtype_tag = DTYPE_WAVEFORM_COMPLEX if is_complex else DTYPE_WAVEFORM_REAL
            
            return {
                '__dtype__': dtype_tag,
                'samples': samples,
                'scalars': scalars,
            }
        
        # Make a copy of numpy arrays to avoid mutation issues
        if isinstance(value, np.ndarray):
            return value.copy()
        
        return value

    # === Anchor-based tracing methods ===

    def add_anchor_watch(self, anchor: ProbeAnchor, config: Optional[WatchConfig] = None) -> None:
        """Add anchor-based watch."""
        if config is None:
            config = WatchConfig(
                var_name=anchor.symbol,
                throttle_strategy=ThrottleStrategy.TIME_BASED,
                throttle_param=50.0
            )
        self._anchor_matcher.add(anchor)
        self._anchor_watches[anchor] = config

    def remove_anchor_watch(self, anchor: ProbeAnchor) -> None:
        """Remove anchor-based watch."""
        self._anchor_matcher.remove(anchor)
        self._anchor_watches.pop(anchor, None)

    def _trace_func(self, frame, event: str, arg) -> Optional[Callable]:
        """
        Trace function with anchor-based matching.

        Uses AnchorMatcher for O(1) lookup.
        Batches all captures from this trace event for atomic GUI updates.
        """
        # Fast exit if disabled
        if not self._enabled:
            return None

        # Always flush pending deferred captures (from previous line/event)
        flushed = self._capture_manager.flush_deferred(
            frame_id=id(frame),
            event=event,
            resolve_value=lambda anchor: self._resolve_anchor_value(frame, anchor),
            get_object_id=lambda anchor: self._get_anchor_object_id(frame, anchor),
        )
        if flushed:
            self._send_record_batch(flushed)

        # Only process 'line' events for new matching
        if event != 'line':
            return self._trace_func

        # Fast file filter
        code = frame.f_code
        filename = code.co_filename

        # Skip frozen/internal modules
        if filename.startswith(self._skip_prefixes):
            return self._trace_func

        # Fast check: does this file have any anchors?
        if not self._anchor_matcher.has_file(filename):
            return self._trace_func

        # Fast check: does this location have any anchors?
        lineno = frame.f_lineno
        if not self._anchor_matcher.has_location(filename, lineno):
            return self._trace_func

        # Get local and global variable names
        local_names = set(frame.f_locals.keys())
        global_names = set(frame.f_globals.keys())
        all_names = local_names | global_names

        # Find matching anchors
        matching_anchors = self._anchor_matcher.match(filename, lineno, all_names)

        if not matching_anchors:
            return self._trace_func
        
        trace_print(f"LINE {lineno}: Matched {len(matching_anchors)} anchors: {[a.symbol for a in matching_anchors]}")

        # Capture for each matching anchor, batching all captures from this event
        timestamp = time.perf_counter_ns()
        location_key = (filename, lineno)
        batch: List[CaptureRecord] = []
        frame_id = id(frame)

        rhs_anchors = [a for a in matching_anchors if not getattr(a, 'is_assignment', False)]
        lhs_anchors = [a for a in matching_anchors if getattr(a, 'is_assignment', False)]

        logical_order = 0
        for anchor in rhs_anchors:
            config = self._anchor_watches.get(anchor)
            if config is None or not config.enabled:
                continue

            # Get the value (check locals first, then globals for module-level vars)
            if anchor.symbol in frame.f_locals:
                value = frame.f_locals[anchor.symbol]
            else:
                value = frame.f_globals[anchor.symbol]

            dtype, shape = classify_data(value)
            serialized_value = self._serialize_value(value)
            record = self._capture_manager.capture_immediate(
                anchor=anchor,
                value=serialized_value,
                dtype=dtype,
                shape=shape,
                timestamp=timestamp,
                logical_order=logical_order,
            )
            logical_order += 1
            trace_print(f"CAPTURE: {anchor.symbol}@{anchor.line} dtype={dtype} (RHS immediate)")

            batch.append(record)

        for anchor in lhs_anchors:
            config = self._anchor_watches.get(anchor)
            if config is None or not config.enabled:
                continue
            # Get current object ID to detect when assignment completes
            old_id = self._get_anchor_object_id(frame, anchor)
            self._capture_manager.defer_capture(
                frame_id=frame_id,
                anchor=anchor,
                logical_order=logical_order,
                timestamp=timestamp,
                old_object_id=old_id,
            )
            logical_order += 1

        # Send batch
        if batch:
            self._send_record_batch(batch)

        return self._trace_func

    def _send_record_batch(self, batch: List[CaptureRecord]) -> None:
        """Send a batch of CaptureRecords to the appropriate callback."""
        trace_print(f"Sending batch of {len(batch)} records")
        try:
            if self._capture_record_batch_callback is not None:
                self._capture_record_batch_callback(batch)
                return

            if self._capture_record_callback is not None:
                for record in batch:
                    self._capture_record_callback(record)
                return

            converted = [(record.anchor, self._record_to_captured(record)) for record in batch]
            if self._anchor_batch_callback is not None:
                self._anchor_batch_callback(converted)
            elif self._anchor_data_callback is not None:
                for anchor, captured in converted:
                    self._anchor_data_callback(anchor, captured)
            else:
                for _, captured in converted:
                    self._data_callback(captured)
        except Exception:
            pass  # Don't let callback errors break tracing

    def _record_to_captured(self, record: CaptureRecord) -> CapturedVariable:
        """Convert CaptureRecord to legacy CapturedVariable for existing callbacks."""
        timestamp_sec = record.timestamp / 1_000_000_000
        return CapturedVariable(
            name=record.anchor.symbol,
            value=record.value,
            dtype=record.dtype,
            shape=record.shape,
            timestamp=timestamp_sec,
            source_file=record.anchor.file,
            line_number=record.anchor.line,
            function_name=record.anchor.func,
        )

    def _resolve_anchor_value(
        self, frame, anchor: ProbeAnchor
    ) -> Tuple[Any, str, Optional[tuple]]:
        """Resolve and serialize a value for a deferred capture."""
        if anchor.symbol in frame.f_locals:
            value = frame.f_locals[anchor.symbol]
        elif anchor.symbol in frame.f_globals:
            value = frame.f_globals[anchor.symbol]
        else:
            raise KeyError(anchor.symbol)

        dtype, shape = classify_data(value)
        serialized_value = self._serialize_value(value)
        return serialized_value, dtype, shape

    def _get_anchor_object_id(
        self, frame, anchor: ProbeAnchor
    ) -> Optional[int]:
        """Get the Python id() of the current value for an anchor.
        
        Returns None if the variable doesn't exist yet.
        """
        if anchor.symbol in frame.f_locals:
            return id(frame.f_locals[anchor.symbol])
        elif anchor.symbol in frame.f_globals:
            return id(frame.f_globals[anchor.symbol])
        else:
            return None

    def start(self) -> None:
        """Start tracing with anchor-based matching."""
        self._enabled = True
        sys.settrace(self._trace_func)

    # Alias for backwards compatibility
    start_anchored = start

    @property
    def anchor_count(self) -> int:
        """Return the number of anchor watches."""
        return len(self._anchor_watches)
