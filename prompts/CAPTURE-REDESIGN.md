# Capture Pipeline Redesign

## Context

PyProbe is a visual variable debugger for Python. Users click on variables in source code to "probe" them, and the values are displayed in real-time graphs/panels as the script executes.

The current capture mechanism has fundamental ordering and data loss issues that need a complete redesign.

## Current Architecture (Flawed)

### Files Involved
- `pyprobe/core/tracer.py` - sys.settrace hook, captures variable values
- `pyprobe/core/deferred_capture.py` - Handles LHS assignment captures (removed; replaced by CaptureManager)
- `pyprobe/core/anchor_matcher.py` - Matches probe locations to trace events
- `pyprobe/ipc/channels.py` - IPC between subprocess (tracer) and GUI

### Current Flow
1. User probes a variable at (file, line, symbol)
2. Tracer uses `sys.settrace` to intercept execution
3. On 'line' events, tracer checks if current location matches any probes
4. For RHS (right-hand side) captures: value captured immediately
5. For LHS (left-hand side/assignment targets): capture deferred to next line
6. Captured values sent via IPC queue to GUI process
7. GUI updates panels with received values

### Current Flaws

#### 1. Throttling Blocks Capture (Not Just Display)
```python
# tracer.py - WRONG approach
if elapsed_ms < self._location_throttle_ms:
    return  # Skips EVERYTHING including deferred capture registration
```
The 50ms throttle was meant to prevent GUI flooding, but it blocks the capture itself. In a tight loop executing in microseconds, only the first iteration is captured.

#### 2. Deferred Capture Uses Object ID Comparison
```python
# deferred_capture.py (removed)
if current_id != old_id:
    ready_to_flush.append(anchor)
```
This assumes object identity changes on assignment. For immutable objects (int, str, tuple), this works. But for mutable objects modified in-place, `id()` doesn't change and the capture is skipped.

#### 3. No Sequence Numbers / Timestamps for Ordering
Captures are sent via multiprocessing Queue without sequence numbers. Queue ordering should be FIFO, but with multiple capture types (immediate vs deferred) and async IPC, ordering can be violated.

#### 4. Flush Only on 'line' Events
Deferred captures only flush when a new 'line' event occurs. If the function returns immediately after an assignment, the deferred capture may be lost or arrive late.

#### 5. No Separation Between Capture and Display
The throttle conflates two concerns:
- **Capture**: Should ALWAYS happen, maintain ordering
- **Display**: Can be throttled to prevent GUI overload

## Required Behavior

### Example 1: Simple Loop LHS Probe
```python
def main():
    x = 10
    for i in range(3):
        x = x - 1  # Probe LHS 'x' here

if __name__ == "__main__":
    main()
```

**Probe**: LHS `x` at line 4
**Expected captures in order**: 9, 8, 7
**Final displayed value**: 7

The probe should see each post-assignment value in execution order.

### Example 2: RHS Probe in Loop
```python
def main():
    x = 10
    for i in range(3):
        y = x - 1  # Probe RHS 'x' here
        x = y
```

**Probe**: RHS `x` at line 4
**Expected captures in order**: 10, 9, 8
**Final displayed value**: 8

RHS captures the value BEFORE the line executes.

### Example 3: Multiple Probes Same Line
```python
x = a + b  # Probe LHS 'x', RHS 'a', RHS 'b'
```

All three captures from the same line should:
1. Be captured atomically (same logical timestamp)
2. Arrive at GUI together or in deterministic order
3. RHS values captured before execution, LHS after

### Example 4: Nested Loops
```python
for i in range(2):
    for j in range(3):
        x = i * 10 + j  # Probe LHS 'x'
```

**Expected captures in order**: 0, 1, 2, 10, 11, 12
**Must maintain strict execution order**.

### Example 5: Fast Tight Loop (Graph Use Case)
```python
for i in range(1000000):
    x = i  # Probe LHS 'x'
```

**Critical Understanding**: PyProbe displays a **graph plotting values over time**. When probing `x`, the graph shows the complete history: x-axis is capture index (or time), y-axis is value.

**Requirements**:
- ALL 1,000,000 values (0, 1, 2, ..., 999999) MUST be captured
- ALL captured values MUST be stored for the graph
- GUI redraws can be throttled (e.g., 60fps) to prevent freezing
- But when the graph redraws, it must show ALL captured data points
- No sampling/dropping of captured values - the graph IS the complete history

**Expected graph**: A line from (0, 0) to (999999, 999999) with all intermediate points.

## Design Requirements

### R1: Separate Capture from GUI Redraw
```
[Capture Layer] -> [Storage Buffer] -> [GUI Redraw Throttle]
     ^                   ^                      ^
     |                   |                      |
   ALWAYS capture    Store ALL values     Only limits redraw rate
   with sequence #   for graph history    Graph shows full buffer
```

**Key distinction**:
- **Capture**: Must happen for EVERY value change (no loss)
- **Storage**: ALL captures stored in per-probe buffer (grows over execution)
- **Redraw**: Can be throttled to 60fps, but each redraw shows complete buffer

### R2: Strict Ordering with Sequence Numbers
Every capture must have:
- `seq_num`: Monotonically increasing per-probe sequence number
- `timestamp`: High-resolution timestamp (time.perf_counter_ns)
- `logical_order`: Execution order (for same-line multi-probe)

### R3: Complete History Preservation
ALL captured values must be preserved for graph display. The graph shows the complete execution history, not just the latest value. Memory management (e.g., ring buffer for very long runs) is a separate concern.

### R4: Atomic Multi-Probe Capture
All probes on the same line should be captured as a batch with:
- Same timestamp
- Sequential `logical_order` within the batch
- Sent as a single IPC message

### R5: Robust Deferred Capture
For LHS probes:
- Register deferred capture with current value snapshot
- Flush on: next 'line' event, 'return' event, 'exception' event
- Don't rely solely on object ID comparison
- Consider value comparison or always-capture approach

### R6: No Data Loss at Boundaries
Captures must not be lost when:
- Function returns (implicit or explicit)
- Exception is raised
- Loop exits
- Script ends

## Suggested Architecture

### Capture Layer (in subprocess)
```python
class CaptureManager:
    def __init__(self):
        self._seq_counter = 0
        self._pending_deferred = {}  # frame_id -> [(anchor, pre_value, seq)]

    def capture_immediate(self, anchor, value, timestamp):
        """Capture RHS value immediately."""
        seq = self._next_seq()
        return CaptureRecord(anchor, value, timestamp, seq, is_deferred=False)

    def defer_capture(self, frame_id, anchor, pre_value, timestamp):
        """Register LHS capture to be completed later."""
        seq = self._next_seq()  # Reserve sequence number NOW
        self._pending_deferred[frame_id].append((anchor, pre_value, seq, timestamp))

    def flush_deferred(self, frame_id, frame):
        """Complete deferred captures, return records."""
        records = []
        for anchor, pre_value, seq, timestamp in self._pending_deferred.pop(frame_id, []):
            post_value = get_value(frame, anchor.symbol)
            records.append(CaptureRecord(anchor, post_value, timestamp, seq, is_deferred=True))
        return records
```

### Queue Layer (IPC)
```python
class OrderedCaptureQueue:
    """Maintains strict ordering, handles batching."""

    def put_batch(self, records: List[CaptureRecord]):
        """Send batch of captures, preserving order."""
        # Sort by seq_num before sending
        records.sort(key=lambda r: r.seq_num)
        self._queue.put(('batch', records))

    def put_end_marker(self):
        """Signal end of capture stream."""
        self._queue.put(('end', None))
```

### Display Layer (GUI side)
```python
class ProbeDataBuffer:
    """Stores ALL captured values for graph display."""

    def __init__(self, anchor):
        self._anchor = anchor
        self._values = []      # All captured values in order
        self._timestamps = []  # Corresponding timestamps
        self._seq_nums = []    # For ordering verification

    def append(self, record: CaptureRecord):
        """Add a capture to the buffer (called for EVERY capture)."""
        # Verify ordering
        if self._seq_nums and record.seq_num <= self._seq_nums[-1]:
            # Out of order! Log warning, but still append
            logger.warning(f"Out of order: got seq {record.seq_num}, last was {self._seq_nums[-1]}")

        self._values.append(record.value)
        self._timestamps.append(record.timestamp)
        self._seq_nums.append(record.seq_num)

    def get_plot_data(self):
        """Return data for graph rendering."""
        return self._timestamps, self._values


class RedrawThrottler:
    """Throttles GUI redraws while preserving ALL data."""

    def __init__(self, min_interval_ms=16):  # ~60 FPS max
        self._buffers = {}  # anchor -> ProbeDataBuffer
        self._last_redraw = 0
        self._min_interval = min_interval_ms / 1000
        self._dirty = set()  # anchors with new data since last redraw

    def receive(self, record: CaptureRecord):
        """Process incoming capture - ALWAYS store, mark dirty."""
        anchor = record.anchor
        if anchor not in self._buffers:
            self._buffers[anchor] = ProbeDataBuffer(anchor)

        self._buffers[anchor].append(record)  # ALWAYS append
        self._dirty.add(anchor)

    def should_redraw(self) -> bool:
        """Check if enough time passed for a redraw."""
        now = time.perf_counter()
        if now - self._last_redraw >= self._min_interval:
            self._last_redraw = now
            return True
        return False

    def get_dirty_buffers(self) -> Dict[Anchor, ProbeDataBuffer]:
        """Get buffers that need redrawing, clear dirty flags."""
        result = {a: self._buffers[a] for a in self._dirty}
        self._dirty.clear()
        return result
```

## Test Cases

### Test 1: Loop Ordering
```python
# Input
x = 10
for i in range(3):
    x = x - 1  # Probe LHS x

# Expected capture sequence (in order)
[
    CaptureRecord(symbol='x', value=9, seq=0),
    CaptureRecord(symbol='x', value=8, seq=1),
    CaptureRecord(symbol='x', value=7, seq=2),
]

# Graph shows: 3 points at y=9, y=8, y=7 (in that x-order)
# NOT: just "7" as final value
```

### Test 2: Multi-probe Same Line
```python
# Input
x = a + b  # Probe: LHS x, RHS a, RHS b (a=1, b=2)

# Expected capture sequence (RHS before LHS)
[
    CaptureRecord(symbol='a', value=1, seq=0, logical_order=0),
    CaptureRecord(symbol='b', value=2, seq=1, logical_order=1),
    CaptureRecord(symbol='x', value=3, seq=2, logical_order=2),  # deferred
]
```

### Test 3: Function Return
```python
def foo():
    x = 42  # Probe LHS x
    return  # No more 'line' events after this

# Expected: x=42 must be captured before function exit
```

### Test 4: High-frequency Loop (Graph Storage)
```python
for i in range(1_000_000):
    x = i  # Probe LHS x

# Expected:
# - ALL 1M values captured and stored in graph buffer
# - Graph shows complete line from (0,0) to (999999, 999999)
# - GUI redraws throttled to ~60fps (not 1M redraws)
# - Each redraw renders the COMPLETE buffer accumulated so far
# - NO data loss - graph contains all 1M points when loop ends
```

## Files to Modify

1. **pyprobe/core/tracer.py** - Rewrite trace function with new capture logic
2. **pyprobe/core/deferred_capture.py** - Replaced by robust CaptureManager (removed)
3. **pyprobe/ipc/messages.py** - Add sequence numbers to capture messages
4. **pyprobe/gui/message_handler.py** - Buffer management, redraw throttling
5. **pyprobe/gui/probe_panel.py** - Graph buffer storage and rendering

## Constraints

- Must work with `sys.settrace` (Python's only tracing mechanism)
- IPC is via `multiprocessing.Queue` (subprocess -> GUI)
- Cannot block the traced script significantly
- GUI must remain responsive during fast loops
- Graph must support efficient append and render of large datasets

## Success Criteria

1. `loop.py` example: graph shows values 9, 8, 7 in order (3 points)
2. Values arrive and are stored in execution order
3. No data loss at function boundaries
4. GUI doesn't freeze on million-iteration loops (redraw throttled)
5. Million-iteration loop: graph contains ALL 1M points when complete
6. Multiple probes on same line maintain logical ordering
