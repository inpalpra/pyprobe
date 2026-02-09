"""
The heart of PyProbe - implements variable interception via sys.settrace
with careful attention to minimizing overhead in tight loops.
"""

import sys
import time
from typing import Dict, Set, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
import numpy as np

from .data_classifier import (
    classify_data, get_waveform_info, get_waveform_collection_info,
    get_array_collection_info,
    DTYPE_WAVEFORM_REAL, DTYPE_WAVEFORM_COLLECTION, DTYPE_ARRAY_COLLECTION
)
from .anchor import ProbeAnchor
from .anchor_matcher import AnchorMatcher
from .deferred_capture import DeferredCaptureManager
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
    3. Throttling checked BEFORE accessing frame.f_locals (expensive)
    """

    def __init__(
        self,
        data_callback: Callable[[CapturedVariable], None],
        target_files: Optional[Set[str]] = None,
        target_functions: Optional[Set[str]] = None,
        anchor_data_callback: Optional[Callable[[ProbeAnchor, CapturedVariable], None]] = None,
        anchor_batch_callback: Optional[Callable[[list], None]] = None
    ):
        """
        Args:
            data_callback: Called when a variable capture passes throttling
            target_files: Only trace these files (None = all files)
            target_functions: Only trace these functions (None = all functions)
            anchor_data_callback: Called for anchor-based captures (anchor, captured_var)
            anchor_batch_callback: Called with list of (anchor, captured_var) tuples from same trace event
        """
        self._data_callback = data_callback
        self._anchor_data_callback = anchor_data_callback
        self._anchor_batch_callback = anchor_batch_callback
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
        
        # Location-based throttle: all anchors at (file, line) share one throttle
        # This ensures probes on same line always capture together
        self._location_throttle: Dict[tuple, float] = {}  # (file, line) -> last_capture_time
        self._location_throttle_ms = 50.0  # Default throttle for location-based captures
        
        # Deferred capture manager for assignment targets
        self._deferred = DeferredCaptureManager()

    def stop(self) -> None:
        """Disable tracing."""
        self._enabled = False
        sys.settrace(None)

    def _value_changed(self, value: Any, config: WatchConfig) -> bool:
        """Check if value changed significantly (for CHANGE_DETECT strategy)."""
        try:
            if isinstance(value, np.ndarray):
                # For arrays, use hash of downsampled data
                step = max(1, len(value.flat) // 100)
                new_hash = hash(value.flat[::step].tobytes())
            else:
                new_hash = hash(value)

            if new_hash == config.last_value_hash:
                return False
            config.last_value_hash = new_hash
            return True
        except (TypeError, ValueError):
            return True  # If we can't hash, always capture

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
            
            return {
                '__dtype__': DTYPE_WAVEFORM_REAL,
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
        flushed = self._deferred.flush(frame, event, self._create_anchor_capture)
        if flushed:
            self._send_batch(flushed)

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

        # Capture for each matching anchor, batching all captures from this event
        current_time = time.perf_counter()
        
        # Location-based throttle: all anchors on this line share one throttle check
        location_key = (filename, lineno)
        last_capture = self._location_throttle.get(location_key, 0.0)
        elapsed_ms = (current_time - last_capture) * 1000
        
        if elapsed_ms < self._location_throttle_ms:
            return self._trace_func  # Skip ALL anchors on this line
        
        batch = []
        frame_id = id(frame)

        for anchor in matching_anchors:
            config = self._anchor_watches.get(anchor)
            if config is None or not config.enabled:
                continue

            # If this is an assignment target, defer capture to next line (post-execution)
            is_assign = getattr(anchor, 'is_assignment', False)
            if is_assign:
                # Record the current object ID (or None if doesn't exist)
                symbol = anchor.symbol
                if symbol in frame.f_locals:
                    old_id = id(frame.f_locals[symbol])
                elif symbol in frame.f_globals:
                    old_id = id(frame.f_globals[symbol])
                else:
                    old_id = None
                self._deferred.defer(frame_id, anchor, lineno, old_id)
                continue

            # Get the value (check locals first, then globals for module-level vars)
            if anchor.symbol in frame.f_locals:
                value = frame.f_locals[anchor.symbol]
            else:
                value = frame.f_globals[anchor.symbol]

            # For CHANGE_DETECT, still check if value changed
            if config and config.throttle_strategy == ThrottleStrategy.CHANGE_DETECT:
                if not self._value_changed(value, config):
                    continue

            # Create capture with anchor context
            captured = self._create_anchor_capture(anchor, value, current_time)
            
            # Debug trace for immediate captures
            if isinstance(value, np.ndarray) and np.iscomplexobj(value):
                trace_print(f"IMMEDIATE CAPTURE: {anchor.symbol} at line {anchor.line}, is_assignment={anchor.is_assignment}, mean={value.mean():.4f}")
            
            batch.append((anchor, captured))
        
        # Update location throttle time if we captured or deferred anything
        if batch or self._deferred.has_pending(frame_id):
            self._location_throttle[location_key] = current_time

        # Send batch
        if batch:
            self._send_batch(batch)

        return self._trace_func

    def _send_batch(self, batch: list) -> None:
        """Send a batch of captures to the appropriate callback."""
        try:
            if self._anchor_batch_callback is not None:
                self._anchor_batch_callback(batch)
            elif self._anchor_data_callback is not None:
                for anchor, captured in batch:
                    self._anchor_data_callback(anchor, captured)
            else:
                for anchor, captured in batch:
                    self._data_callback(captured)
        except Exception:
            pass  # Don't let callback errors break tracing

    def _create_anchor_capture(
        self, anchor: ProbeAnchor, value: Any, timestamp: float
    ) -> CapturedVariable:
        """Create CapturedVariable with anchor context."""
        dtype, shape = classify_data(value)
        serialized_value = self._serialize_value(value)

        return CapturedVariable(
            name=anchor.symbol,
            value=serialized_value,
            dtype=dtype,
            shape=shape,
            timestamp=timestamp,
            source_file=anchor.file,
            line_number=anchor.line,
            function_name=anchor.func
        )

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
