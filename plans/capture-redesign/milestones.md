# Capture Pipeline Redesign - Milestones

> **Reference Documents**:
> - `plans/capture-redesign/architecture.md` - High-level architecture
> - `prompts/CAPTURE-REDESIGN.md` - Detailed requirements and test cases

## Overview

This document outlines sequential milestones to implement the capture pipeline redesign. Each milestone is self-contained with clear inputs, outputs, and verification criteria.

**Important**: Milestones must be completed in order. Each builds on the previous.

---

## Milestone 1: CaptureRecord and Sequence Infrastructure

**Goal**: Establish the foundational data structures for ordered captures.

**Scope**:
- Create `CaptureRecord` dataclass with seq_num, timestamp, logical_order
- Create sequence number generator (thread-safe monotonic counter)
- Add sequence fields to IPC message protocol
- Unit tests for sequence ordering

**Key Files**:
- Create: `pyprobe/core/capture_record.py`
- Modify: `pyprobe/ipc/messages.py` (if exists) or IPC message structures

**Verification**:
- CaptureRecord can be created with all required fields
- Sequence numbers are monotonically increasing
- Records can be serialized/deserialized for IPC

**Does NOT include**:
- Changes to tracer.py
- Changes to GUI
- Actual capture logic changes

---

## Milestone 2: CaptureManager Core

**Goal**: Implement the capture orchestration without deferred capture.

**Scope**:
- Create `CaptureManager` class
- Implement `capture_immediate()` for RHS captures
- Integrate with sequence number generator
- Batch creation for same-event captures
- Unit tests for immediate capture flow

**Key Files**:
- Create: `pyprobe/core/capture_manager.py`
- Reference: `pyprobe/core/tracer.py` (understand current flow, don't modify yet)

**Verification**:
- `capture_immediate()` creates correctly sequenced CaptureRecords
- Multiple captures in same batch have same timestamp, sequential logical_order
- Unit tests pass

**Does NOT include**:
- Deferred capture logic
- Integration with tracer.py
- GUI changes

---

## Milestone 3: Robust Deferred Capture

**Goal**: Implement reliable LHS capture with sequence reservation.

**Scope**:
- Add `defer_capture()` to CaptureManager
- Add `flush_deferred()` with proper event handling (line, return, exception)
- Reserve sequence numbers at defer time (not flush time)
- Handle edge cases: function return after assignment, exceptions
- Unit tests for deferred capture scenarios

**Key Files**:
- Modify: `pyprobe/core/capture_manager.py`
- Reference: `pyprobe/core/deferred_capture.py` (understand current approach)

**Verification**:
- Deferred captures get sequence numbers in correct order relative to immediate captures
- Flush happens on line, return, AND exception events
- No captures lost at function boundaries
- Unit tests cover: loop LHS, function return after assignment, exception during assignment

**Does NOT include**:
- Integration with tracer.py
- Removal of old deferred_capture.py
- GUI changes

---

## Milestone 4: Tracer Integration

**Goal**: Replace old capture logic in tracer.py with CaptureManager.

**Scope**:
- Integrate CaptureManager into VariableTracer
- Remove old throttling logic that blocked captures
- Remove old deferred capture calls
- Keep location-based throttle for DISPLAY hints only (optional metadata)
- End-to-end test: tracer → CaptureRecords

**Key Files**:
- Modify: `pyprobe/core/tracer.py`
- Deprecate/Remove: `pyprobe/core/deferred_capture.py` (after migration)

**Verification**:
- Running test script produces CaptureRecords with correct seq_nums
- Loop test: all iterations captured (not throttled)
- LHS captures have correct post-assignment values
- Order matches execution order

**Does NOT include**:
- IPC changes
- GUI changes

---

## Milestone 5: Ordered IPC Queue

**Goal**: Ensure capture ordering is preserved through IPC.

**Scope**:
- Create `OrderedCaptureQueue` wrapper for multiprocessing.Queue
- Implement batch sending with ordering guarantees
- Add end-of-stream markers
- Integration with tracer's batch sending

**Key Files**:
- Create: `pyprobe/ipc/ordered_queue.py`
- Modify: `pyprobe/ipc/channels.py` (integrate new queue)
- Modify: `pyprobe/core/tracer.py` (use new queue for sending)

**Verification**:
- Batches arrive in send order
- Records within batches maintain sequence order
- End markers properly signal completion
- No message loss under high throughput

**Does NOT include**:
- GUI-side changes
- Buffer management

---

## Milestone 6: ProbeDataBuffer

**Goal**: Implement per-probe storage for complete capture history.

**Scope**:
- Create `ProbeDataBuffer` class
- Store all values, timestamps, sequence numbers
- Verify ordering (log warnings on violations)
- Provide `get_plot_data()` for graph rendering
- Unit tests for buffer operations

**Key Files**:
- Create: `pyprobe/gui/probe_buffer.py`

**Verification**:
- Buffer stores all appended values
- Out-of-order detection works and logs warnings
- `get_plot_data()` returns complete history
- Memory grows appropriately with capture count

**Does NOT include**:
- Integration with message_handler
- Integration with probe_panel
- Redraw throttling

---

## Milestone 7: RedrawThrottler

**Goal**: Separate capture storage from display refresh rate.

**Scope**:
- Create `RedrawThrottler` class
- Track dirty buffers (new data since last redraw)
- Implement ~60 FPS redraw limiting
- Provide API for checking if redraw needed and getting dirty buffers

**Key Files**:
- Create: `pyprobe/gui/redraw_throttler.py`

**Verification**:
- Redraw rate limited to target FPS
- All buffers with new data marked dirty
- Complete buffer contents available on each redraw
- High-frequency captures don't cause high-frequency redraws

**Does NOT include**:
- Integration with actual GUI components
- Message handler changes

---

## Milestone 8: GUI Integration

**Goal**: Connect new capture pipeline to existing GUI components.

**Scope**:
- Integrate ProbeDataBuffer into message_handler.py
- Connect RedrawThrottler to GUI update cycle
- Update probe_panel.py to render from ProbeDataBuffer
- Remove old throttling/buffering logic from GUI

**Key Files**:
- Modify: `pyprobe/gui/message_handler.py`
- Modify: `pyprobe/gui/probe_panel.py`
- Modify: `pyprobe/gui/probe_controller.py` (if needed)

**Verification**:
- Captures flow from tracer to graph display
- Graph shows complete capture history
- GUI remains responsive during fast loops
- No data loss visible in graph

**Does NOT include**:
- Performance optimization
- Memory management for long runs

---

## Milestone 9: End-to-End Testing

**Goal**: Verify all requirements from CAPTURE-REDESIGN.md are met.

**Scope**:
- Test Case 1: Loop ordering (x = x - 1, expect 9, 8, 7)
- Test Case 2: Multi-probe same line
- Test Case 3: Function return (no data loss)
- Test Case 4: High-frequency loop (1M iterations)
- Fix any issues discovered

**Key Files**:
- Create: `tests/test_capture_pipeline.py` (integration tests)
- Modify: Any files with bugs discovered during testing

**Verification**:
- All test cases from CAPTURE-REDESIGN.md pass
- Graph displays correct values in correct order
- No data loss at any boundary
- GUI responsive during stress tests

---

## Milestone 10: Cleanup and Documentation

**Goal**: Remove deprecated code, update documentation.

**Scope**:
- Remove old `deferred_capture.py` if fully replaced
- Remove deprecated throttling code
- Update inline documentation
- Update any user-facing documentation

**Key Files**:
- Delete: `pyprobe/core/deferred_capture.py` (if replaced)
- Modify: Various files for documentation updates

**Verification**:
- No dead code remains
- All tests still pass
- Documentation accurate

---

## Dependency Graph

```
M1 (CaptureRecord)
 │
 ▼
M2 (CaptureManager Core)
 │
 ▼
M3 (Deferred Capture)
 │
 ▼
M4 (Tracer Integration) ──────┐
 │                            │
 ▼                            ▼
M5 (Ordered IPC) ◀───────── M6 (ProbeDataBuffer)
 │                            │
 │                            ▼
 │                         M7 (RedrawThrottler)
 │                            │
 └────────────┬───────────────┘
              │
              ▼
        M8 (GUI Integration)
              │
              ▼
        M9 (E2E Testing)
              │
              ▼
        M10 (Cleanup)
```

Note: M5 (IPC) and M6-M7 (GUI buffers) can be developed in parallel after M4.

---

## For AI Agents

When implementing a milestone:

1. **Read first**:
   - This document (milestones.md)
   - `plans/capture-redesign/architecture.md`
   - `prompts/CAPTURE-REDESIGN.md`
   - Current implementations of files to be modified

2. **Understand scope**: Each milestone has explicit "Does NOT include" items

3. **Write tests**: Create or update tests as specified in Verification

4. **Verify**: Run verification criteria before marking complete

5. **Don't over-engineer**: Implement only what the milestone specifies
