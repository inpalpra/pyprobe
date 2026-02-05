# Plan 4: Tracer Refactor

**Focus:** Modify tracer to support anchor-based probing.

**Branch:** `m1/tracer-refactor`

**Dependencies:** Plan 0 (ProbeAnchor, MessageTypes)

**Complexity:** Medium (M)

**UX Requirements Addressed:**
- Hot-probing: add/remove while running (requirement #4)
- ProbeAnchor-based identification (core requirement)

---

## Files to Create

### `pyprobe/core/anchor_matcher.py`

```python
"""Efficient anchor matching for trace function."""
from typing import Dict, List, Optional, Set, Tuple
from pyprobe.core.anchor import ProbeAnchor

class AnchorMatcher:
    """Index structure for O(1) anchor lookup in trace function.

    Indexed by (file, line) for fast filtering in hot path.
    """

    def __init__(self):
        # Primary index: (file, line) -> list of anchors
        self._by_location: Dict[Tuple[str, int], List[ProbeAnchor]] = {}
        # All anchors set for iteration
        self._all_anchors: Set[ProbeAnchor] = set()

    def add(self, anchor: ProbeAnchor) -> None:
        """Add anchor to index."""
        key = (anchor.file, anchor.line)
        if key not in self._by_location:
            self._by_location[key] = []
        if anchor not in self._all_anchors:
            self._by_location[key].append(anchor)
            self._all_anchors.add(anchor)

    def remove(self, anchor: ProbeAnchor) -> None:
        """Remove anchor from index."""
        key = (anchor.file, anchor.line)
        if key in self._by_location:
            try:
                self._by_location[key].remove(anchor)
                if not self._by_location[key]:
                    del self._by_location[key]
            except ValueError:
                pass
        self._all_anchors.discard(anchor)

    def match(self, file: str, line: int, local_vars: Set[str]) -> List[ProbeAnchor]:
        """Find all matching anchors for a (file, line) with given local variables."""
        key = (file, line)
        candidates = self._by_location.get(key, [])
        return [a for a in candidates if a.symbol in local_vars]

    def has_file(self, file: str) -> bool:
        """Check if any anchors exist for this file."""
        return any(f == file for f, _ in self._by_location.keys())

    def has_location(self, file: str, line: int) -> bool:
        """Check if any anchors exist at this location."""
        return (file, line) in self._by_location

    @property
    def files(self) -> Set[str]:
        return {f for f, _ in self._by_location.keys()}

    @property
    def all_anchors(self) -> Set[ProbeAnchor]:
        return self._all_anchors.copy()

    def clear(self) -> None:
        self._by_location.clear()
        self._all_anchors.clear()
```

---

## Files to Modify

### `pyprobe/core/tracer.py`

**Add new methods (DO NOT remove existing methods for backward compatibility):**

```python
# === M1 ADDITIONS START ===

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.anchor_matcher import AnchorMatcher

class VariableTracer:
    # Add to __init__:
    def __init__(self, ...):
        # ... existing code ...

        # M1: Anchor-based watching
        self._anchor_matcher = AnchorMatcher()
        self._anchor_watches: Dict[ProbeAnchor, WatchConfig] = {}

    def add_anchor_watch(self, anchor: ProbeAnchor, config: Optional[WatchConfig] = None) -> None:
        """Add anchor-based watch (M1)."""
        if config is None:
            config = WatchConfig(
                var_name=anchor.symbol,
                throttle_strategy=ThrottleStrategy.TIME_BASED,
                throttle_param=50.0,
            )
        self._anchor_watches[anchor] = config
        self._anchor_matcher.add(anchor)
        self._watch_names.add(anchor.symbol)  # Legacy compatibility

    def remove_anchor_watch(self, anchor: ProbeAnchor) -> None:
        """Remove anchor-based watch."""
        if anchor in self._anchor_watches:
            del self._anchor_watches[anchor]
            self._anchor_matcher.remove(anchor)
            remaining_symbols = {a.symbol for a in self._anchor_watches.keys()}
            if anchor.symbol not in remaining_symbols:
                self._watch_names.discard(anchor.symbol)

    def _trace_func_anchored(self, frame, event: str, arg):
        """Trace function with anchor matching (M1)."""
        if not self._enabled:
            return None
        if event != 'line':
            return self._trace_func_anchored

        code = frame.f_code
        filename = code.co_filename
        line = frame.f_lineno

        # Early exit filters
        if not self._anchor_matcher.has_file(filename):
            return self._trace_func_anchored
        if not self._anchor_matcher.has_location(filename, line):
            return self._trace_func_anchored

        local_names = set(frame.f_locals.keys())
        matches = self._anchor_matcher.match(filename, line, local_names)
        if not matches:
            return self._trace_func_anchored

        current_time = time.perf_counter()
        for anchor in matches:
            config = self._anchor_watches.get(anchor)
            if not config or not config.enabled:
                continue
            if not self._should_capture(config, current_time):
                continue

            value = frame.f_locals[anchor.symbol]
            captured = self._create_anchor_capture(anchor, value, current_time)
            config.last_send_time = current_time

            try:
                self._data_callback(captured)
            except Exception:
                pass

        return self._trace_func_anchored

    def _create_anchor_capture(self, anchor: ProbeAnchor, value, timestamp: float):
        """Create capture with full anchor context."""
        dtype, shape = classify_data(value)
        if isinstance(value, np.ndarray):
            value = value.copy()
        return CapturedVariable(
            name=anchor.symbol,
            value=value,
            dtype=dtype,
            shape=shape,
            timestamp=timestamp,
            source_file=anchor.file,
            line_number=anchor.line,
            function_name=anchor.func,
        )

    def start_anchored(self) -> None:
        """Start tracing with anchor-based matching."""
        self._enabled = True
        sys.settrace(self._trace_func_anchored)

    @property
    def anchor_count(self) -> int:
        return len(self._anchor_watches)

# === M1 ADDITIONS END ===
```

### `pyprobe/core/runner.py`

**Add handlers in `_handle_command` (DO NOT modify existing handlers):**

```python
# === M1 ADDITIONS START ===

def _handle_command(self, msg: Message) -> None:
    # ... existing handlers ...

    # M1: Anchor-based handlers
    elif msg.msg_type == MessageType.CMD_ADD_PROBE:
        anchor = ProbeAnchor.from_dict(msg.payload['anchor'])
        throttle_ms = msg.payload.get('throttle_ms', 50.0)
        config = WatchConfig(
            var_name=anchor.symbol,
            throttle_strategy=ThrottleStrategy.TIME_BASED,
            throttle_param=throttle_ms,
        )
        self._tracer.add_anchor_watch(anchor, config)

    elif msg.msg_type == MessageType.CMD_REMOVE_PROBE:
        anchor = ProbeAnchor.from_dict(msg.payload['anchor'])
        self._tracer.remove_anchor_watch(anchor)

# In run() method, use start_anchored():
def run(self) -> int:
    # ... setup code ...
    self._tracer.start_anchored()  # M1: Use anchored trace function
    # ... rest of method ...

# === M1 ADDITIONS END ===
```

---

## Verification

```bash
python -c "
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.anchor_matcher import AnchorMatcher

matcher = AnchorMatcher()
anchor = ProbeAnchor('/test.py', 10, 4, 'x', 'foo')
matcher.add(anchor)

matches = matcher.match('/test.py', 10, {'x', 'y', 'z'})
assert len(matches) == 1
assert matches[0].symbol == 'x'
print('AnchorMatcher works!')
"
```

---

## Merge Conflict Risk

**Medium** - Modifies `tracer.py` and `runner.py`, but changes are isolated:
- Adds new methods to `VariableTracer` (no changes to existing methods)
- Adds new `elif` branches in `_handle_command`
- Uses marker comments (`# === M1 ADDITIONS ===`) for clear boundaries
