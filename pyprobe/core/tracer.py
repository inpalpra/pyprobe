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
    2. Watch list stored as set for O(1) lookup
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
        self._watches: Dict[str, WatchConfig] = {}
        self._watch_names: Set[str] = set()  # Fast O(1) lookup
        self._enabled = False
        self._global_throttle_ms = 16.67  # ~60 FPS max update rate

        # Paths to skip (stdlib, site-packages)
        self._skip_prefixes = (
            '<frozen',
            '<string>',
        )

        # M1: Anchor-based watching
        self._anchor_matcher = AnchorMatcher()
        self._anchor_watches: Dict[ProbeAnchor, WatchConfig] = {}
        
        # Location-based throttle: all anchors at (file, line) share one throttle
        # This ensures probes on same line always capture together
        self._location_throttle: Dict[tuple, float] = {}  # (file, line) -> last_capture_time
        self._location_throttle_ms = 50.0  # Default throttle for location-based captures
        
        # Pending deferred captures: frame_id -> list of (anchor, original_line)
        # Used to delay capture of assignment targets until after the line executes
        # We track original_line to only flush when on a DIFFERENT line (statement complete)
        self._pending_deferred: Dict[int, List[tuple]] = {}  # frame_id -> [(anchor, line), ...]

    def add_watch(self, config: WatchConfig) -> None:
        """Add a variable to the watch list."""
        self._watches[config.var_name] = config
        self._watch_names.add(config.var_name)

    def remove_watch(self, var_name: str) -> None:
        """Remove a variable from the watch list."""
        self._watches.pop(var_name, None)
        self._watch_names.discard(var_name)

    def set_throttle(self, var_name: str, strategy: ThrottleStrategy, param: float) -> None:
        """Update throttling for a specific variable."""
        if var_name in self._watches:
            self._watches[var_name].throttle_strategy = strategy
            self._watches[var_name].throttle_param = param

    def start(self) -> None:
        """Enable tracing."""
        self._enabled = True
        sys.settrace(self._trace_func)

    def stop(self) -> None:
        """Disable tracing."""
        self._enabled = False
        sys.settrace(None)

    def _trace_func(self, frame, event: str, arg) -> Optional[Callable]:
        """
        The trace function called by Python interpreter.

        CRITICAL PERFORMANCE PATH - every microsecond counts here.
        """
        # Fast exit if disabled
        if not self._enabled:
            return None

        # Only process 'line' events (not 'call', 'return', 'exception')
        if event != 'line':
            return self._trace_func

        # Fast file filter
        code = frame.f_code
        filename = code.co_filename

        # Skip frozen/internal modules
        if filename.startswith(self._skip_prefixes):
            return self._trace_func

        # Filter to target files if specified
        if self._target_files is not None:
            if filename not in self._target_files:
                return self._trace_func

        # Fast function filter
        if self._target_functions is not None:
            if code.co_name not in self._target_functions:
                return self._trace_func

        # No watches? Nothing to do
        if not self._watch_names:
            return self._trace_func

        # Check if any watched variables are in this frame's locals
        # Use set intersection for O(min(watches, locals))
        local_names = set(frame.f_locals.keys())
        watched_in_frame = self._watch_names & local_names

        if not watched_in_frame:
            return self._trace_func

        # Now check throttling and capture
        current_time = time.perf_counter()

        for var_name in watched_in_frame:
            config = self._watches[var_name]

            if not config.enabled:
                continue

            # Throttle check (BEFORE accessing the value)
            if not self._should_capture(config, current_time):
                continue

            # Now access the variable value
            value = frame.f_locals[var_name]

            # For CHANGE_DETECT, check if value actually changed
            if config.throttle_strategy == ThrottleStrategy.CHANGE_DETECT:
                if not self._value_changed(value, config):
                    continue

            # Classify and capture
            captured = self._create_capture(
                var_name, value, filename,
                frame.f_lineno, code.co_name, current_time
            )

            # Update throttle state
            config.last_send_time = current_time
            if config.throttle_strategy == ThrottleStrategy.SAMPLE_EVERY_N:
                config.iteration_count = 0  # Reset after capture

            # Send to callback (non-blocking)
            try:
                self._data_callback(captured)
            except Exception:
                pass  # Don't let callback errors break tracing

        return self._trace_func

    def _should_capture(self, config: WatchConfig, current_time: float) -> bool:
        """Check if we should capture based on throttle strategy."""
        strategy = config.throttle_strategy

        if strategy == ThrottleStrategy.NONE:
            return True

        elif strategy == ThrottleStrategy.TIME_BASED:
            elapsed_ms = (current_time - config.last_send_time) * 1000
            return elapsed_ms >= config.throttle_param

        elif strategy == ThrottleStrategy.SAMPLE_EVERY_N:
            config.iteration_count += 1
            return config.iteration_count >= config.throttle_param

        elif strategy == ThrottleStrategy.CHANGE_DETECT:
            # Still apply a minimum time throttle
            elapsed_ms = (current_time - config.last_send_time) * 1000
            return elapsed_ms >= self._global_throttle_ms

        return True

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

    def _create_capture(
        self, name: str, value: Any, filename: str,
        lineno: int, func_name: str, timestamp: float
    ) -> CapturedVariable:
        """Create a CapturedVariable with proper type classification."""
        dtype, shape = classify_data(value)
        serialized_value = self._serialize_value(value)

        return CapturedVariable(
            name=name,
            value=serialized_value,
            dtype=dtype,
            shape=shape,
            timestamp=timestamp,
            source_file=filename,
            line_number=lineno,
            function_name=func_name
        )

    # === M1: Anchor-based tracing methods ===

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

    def _flush_deferred(self, frame, event: str) -> None:
        """
        Process any pending deferred captures for this frame.
        
        Only flushes captures when:
        1. Event is 'line' (a new statement is starting)
        2. We're on a DIFFERENT line than where they were deferred
        
        This ensures multi-line statements complete before capture.
        
        Args:
            frame: The current stack frame
            event: The trace event type ('line', 'return', 'call', 'exception')
        """
        # Only flush on 'line' events - this ensures the previous statement completed
        # Non-'line' events (like 'return' from np.array) happen during expression evaluation
        if event != 'line':
            return
        
        # Determine relevant frame ID
        frame_id = id(frame)
        
        # Check if we have pending deferred anchors
        pending = self._pending_deferred.get(frame_id)
        if not pending:
            return
        
        # Check if variables are available in scope (assignment completed)
        # Python 3.11+ generates 'line' events within multi-line expressions,
        # so we can't rely on line numbers. Instead, check if var exists.
        ready_to_flush = []
        still_pending = []
        
        for anchor, original_line in pending:
            symbol = anchor.symbol
            # Variable is ready if it exists in locals OR globals
            var_exists = symbol in frame.f_locals or symbol in frame.f_globals
            if var_exists:
                ready_to_flush.append(anchor)
            else:
                still_pending.append((anchor, original_line))
        
        # Update pending: remove if empty, otherwise keep still_pending items
        if still_pending:
            self._pending_deferred[frame_id] = still_pending
        else:
            self._pending_deferred.pop(frame_id, None)
        
        if not ready_to_flush:
            return

        # Capture them using current state
        current_time = time.perf_counter()
        batch = []
        
        # Use valid frame for locals
        eval_frame = frame
        
        for anchor in ready_to_flush:
            try:

                
                # Value should now be available in locals or globals (post-execution)
                if anchor.symbol in eval_frame.f_locals:
                    value = eval_frame.f_locals[anchor.symbol]
                else:
                    value = eval_frame.f_globals[anchor.symbol]
                
                # Check mapping for Change Detect if needed (omitted for brevity, assume simple capture)
                # Note: throttle check was already done when we deferred it.
                
                captured = self._create_anchor_capture(anchor, value, current_time)
                batch.append((anchor, captured))
            except KeyError as e:
                # Variable might have gone out of scope or not been assigned

                continue
            except Exception:
                continue
                
        # Send batch
        if batch:
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
                pass


    def _trace_func_anchored(self, frame, event: str, arg) -> Optional[Callable]:
        """
        Trace function with anchor-based matching.

        Similar to _trace_func but uses AnchorMatcher for O(1) lookup.
        Batches all captures from this trace event for atomic GUI updates.
        """
        # Fast exit if disabled
        if not self._enabled:
            return None

        # Always flush pending deferred captures (from previous line/event)
        self._flush_deferred(frame, event)

        # Only process 'line' events for new matching
        if event != 'line':
            return self._trace_func_anchored

        # Fast file filter
        code = frame.f_code
        filename = code.co_filename

        # Skip frozen/internal modules
        if filename.startswith(self._skip_prefixes):
            return self._trace_func_anchored

        # Fast check: does this file have any anchors?
        if not self._anchor_matcher.has_file(filename):
            return self._trace_func_anchored

        # Fast check: does this location have any anchors?
        lineno = frame.f_lineno
        if not self._anchor_matcher.has_location(filename, lineno):
            return self._trace_func_anchored

        # Get local and global variable names
        local_names = set(frame.f_locals.keys())
        global_names = set(frame.f_globals.keys())
        all_names = local_names | global_names

        # Find matching anchors
        matching_anchors = self._anchor_matcher.match(filename, lineno, all_names)
        


        if not matching_anchors:
            return self._trace_func_anchored

        # Capture for each matching anchor, batching all captures from this event
        current_time = time.perf_counter()
        
        # Location-based throttle: all anchors on this line share one throttle check
        # This ensures probes on same line ALWAYS capture together (same frame)
        location_key = (filename, lineno)
        last_capture = self._location_throttle.get(location_key, 0.0)
        elapsed_ms = (current_time - last_capture) * 1000
        
        if elapsed_ms < self._location_throttle_ms:
            return self._trace_func_anchored  # Skip ALL anchors on this line
        
        # Initialize batch with any flushed captures (if we want to combine them)
        # But flushed captures were already sent in _flush_deferred (or ideally added to a common batch context)
        # For simplicity, we'll let _flush_deferred send its own batch, and we send ours.
        # Merging them would require passing a 'batch' list to _flush_deferred.
        batch = []

        for anchor in matching_anchors:
            config = self._anchor_watches.get(anchor)
            if config is None or not config.enabled:
                continue

            # NO per-anchor throttle check - location throttle handles it
            
            # If this is an assignment target, defer capture to next line (post-execution)
            is_assign = getattr(anchor, 'is_assignment', False)
            if is_assign:
                frame_id = id(frame)
                if frame_id not in self._pending_deferred:
                    self._pending_deferred[frame_id] = []
                # Store (anchor, original_line) so we only flush when on a different line
                self._pending_deferred[frame_id].append((anchor, lineno))
                continue

            # Get the value (check locals first, then globals for module-level vars)
            if anchor.symbol in frame.f_locals:
                value = frame.f_locals[anchor.symbol]
            else:
                value = frame.f_globals[anchor.symbol]

            # For CHANGE_DETECT, still check if value changed (optional per-anchor)
            if config and config.throttle_strategy == ThrottleStrategy.CHANGE_DETECT:
                if not self._value_changed(value, config):
                    continue

            # Create capture with anchor context
            captured = self._create_anchor_capture(anchor, value, current_time)

            batch.append((anchor, captured))
        
        # Update location throttle time if we captured anything (or deferred anything)
        if batch or (id(frame) in self._pending_deferred and self._pending_deferred[id(frame)]):
            self._location_throttle[location_key] = current_time

        # Send batch to callback (prefer batch callback for atomic updates)
        if batch:
            try:
                if self._anchor_batch_callback is not None:
                    self._anchor_batch_callback(batch)
                elif self._anchor_data_callback is not None:
                    # Fallback: send individually
                    for anchor, captured in batch:
                        self._anchor_data_callback(anchor, captured)
                else:
                    # Ultimate fallback
                    for anchor, captured in batch:
                        self._data_callback(captured)
            except Exception:
                pass

        return self._trace_func_anchored

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

    def start_anchored(self) -> None:
        """Start tracing with anchor-based matching."""
        self._enabled = True
        sys.settrace(self._trace_func_anchored)

    @property
    def anchor_count(self) -> int:
        """Return the number of anchor watches."""
        return len(self._anchor_watches)
