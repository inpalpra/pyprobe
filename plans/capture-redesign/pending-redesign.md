# Pending Capture Redesign Work

> **Reference**: `plans/capture-redesign/architecture.md`
> **Date**: 2026-02-10

## Summary

The capture pipeline has been **partially implemented**. Core components exist but there are gaps between the architecture spec and current implementation.

## Implementation Status

### ✅ Implemented

| Component | File | Architecture Spec | Status |
|-----------|------|-------------------|--------|
| CaptureRecord | `core/capture_record.py` | Dataclass with seq_num, timestamp, logical_order | ✅ Complete |
| CaptureManager | `core/capture_manager.py` | Seq numbering, deferred capture, batch capture | ✅ Complete |
| ProbeDataBuffer | `gui/probe_buffer.py` | Per-probe history, seq ordering verification | ✅ Complete |
| RedrawThrottler | `gui/redraw_throttler.py` | Dirty tracking, FPS limiting, buffer management | ✅ Complete |

### ❌ Not Implemented

| Component | Spec File | Status |
|-----------|-----------|--------|
| OrderedCaptureQueue | `ipc/ordered_queue.py` | ❌ **MISSING** - spec says new file |

### ⚠️ Partial / Differences

| Component | Spec | Actual | Gap |
|-----------|------|--------|-----|
| `ipc/channels.py` | "Use OrderedCaptureQueue" | Uses standard `mp.Queue` | No ordering wrapper |
| CaptureRecord | `is_deferred: bool` field | Not present | Minor - not needed for current use |

## Detailed Gaps

### 1. OrderedCaptureQueue Not Created

**Architecture says:**
```
Location: pyprobe/ipc/ordered_queue.py (new file)

Responsibilities:
- Wrap multiprocessing.Queue with ordering guarantees
- Batch captures from same trace event
- Sort batches by sequence number before sending
- Provide end-of-stream markers
```

**Current state:** File does not exist. `channels.py` uses raw `mp.Queue` directly.

**Impact:** Ordering is currently handled by:
- Sequence numbers assigned in CaptureManager (correct)
- ProbeDataBuffer logs warnings on out-of-order (detection only)
- No explicit sorting or batching at IPC layer

**Risk:** Low for single-probe. Potentially problematic for multi-probe same-line scenarios where IPC ordering matters.

### 2. is_deferred Field Missing

**Architecture says:**
```python
@dataclass
class CaptureRecord:
    ...
    is_deferred: bool       # True for LHS captures
```

**Current state:** CaptureRecord lacks `is_deferred` field.

**Impact:** Can't distinguish LHS vs RHS captures in GUI. Minor - only needed for debugging/visualization.

### 3. End-of-Stream Markers

**Architecture says:** OrderedCaptureQueue should "Provide end-of-stream markers"

**Current state:** Script end is signaled via `DATA_SCRIPT_END` message type, not dedicated marker.

**Impact:** Works but not as clean as architecture intended.

## Recommendations

### High Priority

1. **Create `ipc/ordered_queue.py`** - Even as a thin wrapper that just passes through, having the abstraction in place allows future improvements.

### Low Priority

2. **Add `is_deferred` field to CaptureRecord** - Useful for debugging but not functionally required.

3. **Batch sorting at IPC layer** - Currently relies on captures being sent in order from tracer. Adding explicit sorting would be more robust.

## Working Correctly

Despite the gaps, the current implementation **functions correctly** for most use cases:

- ✅ Sequence numbers assigned at capture time (D1)
- ✅ Always capture, throttle only display (D2)
- ✅ Deferred capture flushes on line/return/exception (D3)
- ✅ RedrawThrottler tracks dirty buffers and limits FPS
- ✅ ProbeDataBuffer stores complete history with ordering verification

## Verification

The CLI automation test (`tests/test_cli_automation.py`) now verifies:
- Script executes and ends correctly
- GUI receives probe data
- **Actual plotted values match expected** (9.0, 8.0, 7.0 for loop.py)
