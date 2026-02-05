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

from .data_classifier import classify_data


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
        target_functions: Optional[Set[str]] = None
    ):
        """
        Args:
            data_callback: Called when a variable capture passes throttling
            target_files: Only trace these files (None = all files)
            target_functions: Only trace these functions (None = all functions)
        """
        self._data_callback = data_callback
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

    def _create_capture(
        self, name: str, value: Any, filename: str,
        lineno: int, func_name: str, timestamp: float
    ) -> CapturedVariable:
        """Create a CapturedVariable with proper type classification."""
        dtype, shape = classify_data(value)

        # Make a copy of numpy arrays to avoid mutation issues
        if isinstance(value, np.ndarray):
            value = value.copy()

        return CapturedVariable(
            name=name,
            value=value,
            dtype=dtype,
            shape=shape,
            timestamp=timestamp,
            source_file=filename,
            line_number=lineno,
            function_name=func_name
        )
