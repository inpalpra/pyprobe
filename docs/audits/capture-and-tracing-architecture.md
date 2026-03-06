Below is an audit of the capture and tracing architecture.

The analysis focuses strictly on:
```
- ProbeAnchor semantics
- CaptureRecord lifecycle
- Sequence numbering and logical ordering guarantees
- Tracer → IPC → GUI data flow
- Determinism under loops / recursion / re-assignment / nested scopes
- Global vs per-session state
```

---

## Conceptual Capture Model

### Runtime Capture Pipeline

```text
Python VM (sys.settrace)
        │
        ▼
VariableTracer._trace_func_impl
        │
        ├─ AnchorMatcher (O(1) location filter)
        │
        ├─ CaptureManager
        │    ├─ capture_immediate()   → RHS values
        │    ├─ defer_capture()       → LHS (pre-assignment)
        │    └─ flush_deferred()      → post-line/return/exception
        │
        ▼
CaptureRecord (immutable)
        │
        ▼
ScriptRunner (subprocess)
        │
        ├─ make_probe_value_msg / batch_msg
        ▼
IPCChannel (multiprocessing queues)
        │
        ▼
GUI process
        │
        ├─ Probe buffer
        ├─ Redraw throttler
        └─ Plot widgets
```

### CaptureRecord Ordering Fields

Each CaptureRecord contains:

```
- seq_num — global monotonic integer
- timestamp — nanosecond clock (perf_counter_ns)
- logical_order — intra-event ordering (batch position)
```

Effective ordering key:

(seq_num)        # primary

logical_order only applies within same trace event.
timestamp is informational, not authoritative.

---

## ProbeAnchor Semantics

### Identity Model

ProbeAnchor is:
```
- Frozen dataclass
- Identified by:
    - absolute file path
    - line
    - column
    - symbol
    - enclosing function
    - is_assignment
```

This is a location-bound identity, not a variable identity.

#### Strengths

```
- Immutable and hashable
- Can survive GUI restarts via persistence
- Differentiates LHS vs RHS semantics
- Scope-aware via func
```

#### Structural Observations

```
- Anchor identity is static.
- Runtime matching depends on (file, line) filter first.
- symbol existence in frame.f_locals gates capture.
```

This means capture semantics are:

“When execution hits this file+line and the local namespace contains this symbol.”

This is location-driven, not variable-instance-driven.

---

## CaptureRecord Lifecycle

### Immediate (RHS)

```
- Trace event: "line"
- Anchor matched
- Value read from frame
- capture_immediate() called
- Sequence number assigned
- Record emitted immediately (batched per event)
```


### Deferred (LHS)

```
- Assignment target detected
- defer_capture() reserves sequence number
- _DeferredItem stored by frame_id
- On next event (line, return, exception):
    - Object ID comparison (optional)
    - Value resolved
    - CaptureRecord created with original reserved seq_num
```

### Key Invariant

Deferred capture sequence numbers are allocated before assignment, but flushed after assignment.

This is correct if and only if:
- Flush always occurs before next logical execution step
- No interleaving across frames breaks ordering

---

## Sequence Numbering & Logical Ordering

### What Is Guaranteed
- SequenceGenerator is thread-safe.
- Monotonic across entire tracer lifetime.
- Per-process (subprocess-local).

Within a single ScriptRunner:

seq_num is strictly increasing

### Across Batches
- logical_order preserves within-line ordering.
- GUI can reconstruct intra-line order deterministically.

### What Is NOT Formally Guaranteed
- No explicit ordering key defined beyond seq_num.
- No formal spec declaring:
“The global ordering invariant of the system is seq_num monotonicity.”

It is currently an implementation property, not a declared invariant.

This matters architecturally.

---

## Tracer → IPC → GUI Data Flow

### Architecture
- Tracer runs in subprocess.
- IPC uses multiprocessing queues.
- Messages are serialized (pickle-compatible payload).
- GUI polls and batches.

### Ordering Guarantees

Multiprocessing Queue preserves FIFO per producer thread.

Because:
- ScriptRunner sends messages serially.
- No concurrent writers to _ipc._data_queue.

Ordering across messages is preserved.

However:

- If multiple trace events happen before GUI processes them,
- If GUI throttling drops or coalesces,

Visual ordering may differ from capture ordering.

Capture ordering is preserved in data.
Render ordering is not necessarily real-time.

---

## Determinism Under Specific Constructs

### Tight Loops

Risk factors:
- High-frequency trace events.
- Throttling is disabled for anchor watches by default (ThrottleStrategy.NONE).
- Potential IPC saturation.

Sequence ordering remains deterministic.
Delivery timing does not.

Scaling risk: high.

### Recursion

Each frame has its own frame_id key for deferred captures.

Deferred state stored as:

_pending: Dict[frame_id, List[_DeferredItem]]

This is structurally correct.

However:
- Frame identity uses id(frame)
- Python may reuse memory after frame destruction
- If deferred state is not fully cleared, theoretical collision risk exists

Currently low probability, but not formally defended.

### Re-assignment

LHS handling uses:

old_object_id
get_object_id(anchor)

This attempts to detect when assignment actually changes object.

Correctness depends on:
- Identity change semantics
- Mutable objects with in-place modification not changing id()

Example:

arr[0] = 5

No new object ID.
Deferred flush may not trigger as expected.

Thus:

Reassignment semantics are correct for rebinding.
Not correct for in-place mutation.

This is an implicit semantic limitation.

### Nested Scopes / Shadowing

Matching uses:

if anchor.symbol in local_vars

No qualification by:
- frame depth
- lexical scope
- closure resolution

If variable shadowed in inner function with same name:

Anchor matches based on file+line, not on runtime function identity.

func exists in ProbeAnchor, but AnchorMatcher does not enforce function match at runtime.

Thus:

Nested scope determinism depends on correct file+line matching only.

---

## Global vs Per-Session State

### Per-Session
- SequenceGenerator
- CaptureManager
- AnchorMatcher
- VariableTracer

All are per ScriptRunner instance.

Good isolation.

### Global Elements
- No global sequence across sessions.
- GUI state may persist probe definitions via sidecar.

No global cross-process capture state.

Architecture is cleanly session-scoped.

---

## Evaluation Against Your Audit Criteria

### Is Logical Ordering First-Class?

No.

It is an emergent property of:
- Monotonic seq_num
- FIFO IPC
- Batch emission

There is no explicit architectural statement:

“Capture ordering is defined solely by seq_num and must never regress.”

Recommendation:
Make ordering an explicit invariant in CaptureManager documentation.

### Does Correctness Depend on Incidental Timing?

Partially yes.

Specifically:
- Deferred flush relies on next "line" event.
- If no further line event occurs (e.g., last line of script),
flush_all() during stop handles it — but this is shutdown dependent.

If tracer stopped unexpectedly:
- Deferred captures could be lost.

Thus:
Correctness partially depends on proper lifecycle sequencing.

### Will This Scale to High-Frequency Capture?

Current constraints:
- sys.settrace overhead
- Python-level matching
- IPC queue overhead
- Serialization copying arrays
- No backpressure mechanism

For tight DSP loops (100k+ iterations per second):

Risks:
- IPC backlog
- GUI lag
- Memory growth
- Increased latency

No drop policy exists at capture level.

Scaling risk: High under extreme load.

### Hidden Coupling Between Tracer and GUI

Coupling points:
- GUI expects batch messages for atomic update.
- Logical ordering implicitly assumed by GUI rendering.
- ThrottleStrategy.NONE forced for anchor watches (testing bias).
- Serialization shape influences widget selection.

Tracer semantics assume GUI understands:
- logical_order
- seq_num
- waveform dict encoding

This is structural coupling.

Not inherently bad, but currently implicit.

### Are Capture Semantics Formally Defined?

No formal specification exists for:
- When LHS capture should occur
- Whether in-place mutation is captured
- Whether capture reflects pre- or post-evaluation
- Whether return event captures final value

Semantics are encoded in implementation.

This is risky long-term.

---

## Structural Strengths
- Clean separation of:
    - Matching
    - Capture orchestration
    - Serialization
    - Transport
- Deferred capture design is conceptually sound.
- Monotonic ordering via SequenceGenerator is robust.
- Frame-scoped pending state handles recursion properly.
- Batch capture ensures atomic GUI update per line.

Architecturally solid foundation.

---

## Determinism Risks

Ranked highest first:
- In-place mutation not captured deterministically.
- Deferred flush timing dependent on trace events.
- No explicit invariant guarding ordering guarantees.
- Frame ID reuse theoretical risk.
- Shadowing ambiguity if file+line reused in nested scopes.

---

## Scaling Risks
- No capture-level throttling for anchors.
- No IPC backpressure.
- Array copying per capture (large memory overhead).
- GUI-side redraw throttling disconnected from capture rate.
- No adaptive sampling.

Under high-frequency DSP loops, saturation is likely.

---

## Refactor Opportunities (Ranked by Architectural Impact)

### Tier 1 — Formalize Invariants (High Impact)
- Define global capture ordering invariant:

ORDER_KEY = (seq_num)

- Explicitly document LHS semantics.
- Define mutation vs rebinding capture behavior.

### Tier 2 — Decouple Capture from Transport
- Introduce bounded ring buffer in subprocess.
- Add backpressure signal from GUI.
- Add capture throttling independent of watch throttle.

### Tier 3 — Determinism Hardening
- Replace frame_id = id(frame) with composite key:

(frame.f_code, frame.f_lineno, frame.f_lasti)

- Enforce function match at runtime when anchor.func set.
- Explicit flush-before-stop guard with stronger guarantees.

### Tier 4 — Performance Scaling
- Optional C-extension trace filter
- Bytecode instrumentation instead of sys.settrace
- Zero-copy shared memory for arrays
- Adaptive capture suppression

---

## Confidence Level in Capture Correctness Under Load

| Scenario | Confidence |
| :--- | :--- |
| Simple scripts | High (9/10) |
| Moderate DSP loops (~100 Hz capture) | Medium-High |
| Tight inner loops (kHz+) | Medium |
| Extreme high-frequency capture | Low-Medium |
| Heavy recursion | Medium |
| In-place mutation tracking | Low |

Overall systemic confidence:

**7 / 10** under normal DSP debugging loads
**4–5 / 10** under extreme high-frequency capture without throttling

---

## Executive Summary
- The architecture is structurally sound.
- Ordering is reliable but not formally codified.
- Deferred capture design is conceptually correct but timing-dependent.
- Scaling limitations exist due to Python tracing and IPC overhead.
- Some semantics (mutation vs rebinding) are implied, not defined.

This system is well-built for its intended debugging domain, but not yet hardened to “formal runtime capture model” standards.

If desired, next step could be:
- Convert this into a formal Capture Model Specification document suitable for long-term maintainability and architectural governance.