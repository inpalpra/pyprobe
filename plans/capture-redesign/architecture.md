# Capture Pipeline Architecture

> **Reference**: See `prompts/CAPTURE-REDESIGN.md` for detailed requirements, examples, and current flaws.

## Overview

PyProbe's capture pipeline moves variable values from a traced Python subprocess to the GUI for graph display. The redesign separates **capture** (always happens) from **display** (throttled) to ensure no data loss while maintaining GUI responsiveness.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SUBPROCESS (Tracer)                               │
│                                                                             │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────────────┐   │
│  │  sys.settrace │───▶│  CaptureManager   │───▶│  OrderedCaptureQueue   │   │
│  │  trace_func   │    │                  │    │                         │   │
│  └──────────────┘    │  - seq_counter   │    │  - Batches captures     │   │
│                       │  - deferred mgmt │    │  - Maintains order      │   │
│                       │  - immediate cap │    │  - IPC to GUI           │   │
│                       └──────────────────┘    └───────────┬─────────────┘   │
│                                                           │                 │
└───────────────────────────────────────────────────────────┼─────────────────┘
                                                            │
                                    multiprocessing.Queue   │
                                                            ▼
┌───────────────────────────────────────────────────────────┼─────────────────┐
│                              GUI PROCESS                  │                 │
│                                                           │                 │
│  ┌────────────────────────────────────────────────────────▼──────────────┐  │
│  │                        MessageHandler                                 │  │
│  │  - Receives batches from queue                                        │  │
│  │  - Dispatches to ProbeDataBuffers                                     │  │
│  └────────────────────────────────────────────────────────┬──────────────┘  │
│                                                           │                 │
│  ┌────────────────────────────────────────────────────────▼──────────────┐  │
│  │                    ProbeDataBuffer (per anchor)                       │  │
│  │  - Stores ALL captured values (complete history)                      │  │
│  │  - Maintains timestamps and sequence numbers                          │  │
│  │  - Verifies ordering, logs warnings on violations                     │  │
│  └────────────────────────────────────────────────────────┬──────────────┘  │
│                                                           │                 │
│  ┌────────────────────────────────────────────────────────▼──────────────┐  │
│  │                       RedrawThrottler                                 │  │
│  │  - Tracks dirty buffers (new data since last redraw)                  │  │
│  │  - Limits redraw rate (~60 FPS)                                       │  │
│  │  - Each redraw renders COMPLETE buffer                                │  │
│  └────────────────────────────────────────────────────────┬──────────────┘  │
│                                                           │                 │
│  ┌────────────────────────────────────────────────────────▼──────────────┐  │
│  │                        ProbePanel (Graph)                             │  │
│  │  - Renders all data points from buffer                                │  │
│  │  - X-axis: capture index (or timestamp)                               │  │
│  │  - Y-axis: captured value                                             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. CaptureManager (Subprocess)

**Location**: `pyprobe/core/capture_manager.py` (new file)

**Responsibilities**:
- Assign monotonically increasing sequence numbers to ALL captures
- Manage deferred captures for LHS (assignment targets)
- Flush deferred captures on: line events, return events, exception events
- Never drop captures due to throttling

**Key Data**:
```python
@dataclass
class CaptureRecord:
    anchor: ProbeAnchor
    value: Any              # Serialized value
    seq_num: int            # Global sequence number
    timestamp: float        # time.perf_counter_ns()
    logical_order: int      # Order within same-line batch
    is_deferred: bool       # True for LHS captures
```

### 2. OrderedCaptureQueue (IPC)

**Location**: `pyprobe/ipc/ordered_queue.py` (new file)

**Responsibilities**:
- Wrap `multiprocessing.Queue` with ordering guarantees
- Batch captures from same trace event
- Sort batches by sequence number before sending
- Provide end-of-stream markers

### 3. ProbeDataBuffer (GUI)

**Location**: `pyprobe/gui/probe_buffer.py` (new file)

**Responsibilities**:
- Store complete capture history for one probe
- Verify sequence ordering (log warnings on violations)
- Provide data for graph rendering
- Handle memory management for very long runs (future: ring buffer option)

### 4. RedrawThrottler (GUI)

**Location**: `pyprobe/gui/redraw_throttler.py` (new file)

**Responsibilities**:
- Track which buffers have new data ("dirty")
- Limit GUI redraw rate to ~60 FPS
- Ensure each redraw shows complete buffer contents

## Key Design Decisions

### D1: Sequence Numbers Assigned at Capture Time

Sequence numbers are assigned in the subprocess when the capture is created, not when sent or received. This ensures:
- Deferred captures get correct ordering relative to immediate captures
- IPC delays don't affect ordering
- Multi-probe same-line captures get sequential numbers in logical order

### D2: Always Capture, Throttle Only Display

The current flaw conflates capture and display throttling. The new design:
- **Capture**: Always happens for every value change (no throttling)
- **Storage**: All values stored in per-probe buffers
- **Display**: Redraw rate limited to prevent GUI freezing

### D3: Deferred Capture Reliability

The new deferred capture mechanism:
- Always flushes on next line, return, AND exception events
- Does not rely solely on object ID comparison
- Reserves sequence numbers when deferred (not when flushed)
- Handles function returns immediately after assignments

### D4: Batch Processing

All captures from a single trace event are batched:
- Same timestamp for all captures in batch
- Sequential logical_order within batch
- Sent as single IPC message to reduce overhead

## Files to Create/Modify

### New Files
| File | Purpose |
|------|---------|
| `pyprobe/core/capture_manager.py` | Sequence numbering, deferred capture |
| `pyprobe/core/capture_record.py` | CaptureRecord dataclass |
| `pyprobe/ipc/ordered_queue.py` | Ordered IPC wrapper |
| `pyprobe/gui/probe_buffer.py` | Per-probe value storage |
| `pyprobe/gui/redraw_throttler.py` | Display throttling |

### Modified Files
| File | Changes |
|------|---------|
| `pyprobe/core/tracer.py` | Use CaptureManager, remove throttle logic |
| `pyprobe/core/deferred_capture.py` | Integrate with CaptureManager or replace |
| `pyprobe/ipc/channels.py` | Use OrderedCaptureQueue |
| `pyprobe/gui/message_handler.py` | Route to ProbeDataBuffers |
| `pyprobe/gui/probe_panel.py` | Render from ProbeDataBuffer |

## Data Flow

### Immediate Capture (RHS)
```
1. trace_func receives 'line' event
2. AnchorMatcher finds matching probes
3. For RHS probe: CaptureManager.capture_immediate()
   - Assigns seq_num
   - Creates CaptureRecord
4. Record added to current batch
5. Batch sent via OrderedCaptureQueue
6. GUI receives, stores in ProbeDataBuffer
7. RedrawThrottler marks buffer dirty
8. On next redraw cycle: graph renders all buffered values
```

### Deferred Capture (LHS)
```
1. trace_func receives 'line' event
2. AnchorMatcher finds LHS probe
3. CaptureManager.defer_capture()
   - Reserves seq_num NOW
   - Records pending capture with pre-value snapshot
4. Next 'line'/'return'/'exception' event
5. CaptureManager.flush_deferred()
   - Captures post-assignment value
   - Creates CaptureRecord with reserved seq_num
6. Record added to batch, sent to GUI
7. GUI stores, marks dirty, redraws on cycle
```

## Success Metrics

1. **No Data Loss**: All captured values visible in graph
2. **Correct Ordering**: Values appear in execution order
3. **GUI Responsiveness**: No freezing on million-iteration loops
4. **Boundary Handling**: Captures not lost at function returns
5. **Multi-Probe Consistency**: Same-line probes maintain logical order
