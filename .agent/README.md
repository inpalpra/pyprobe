# PYPROBE AI README
> AI-optmzd doc. No prose. Max density. Update on every lesson lrnd.

## FIRST: READ THIS
1. Check LESSONS section before debugging - may already be solved
2. After fixing bug → run `@[prompts/END.md]` to log lesson
3. If pattern discovered → add to GOTCHAS

## PROJ OVERVIEW
- PyProbe: visual var prober 4 Python DSP debugging
- M1 milestone: source-anchored probing (click var in code → probe panel appears)
- GUI: PyQt6, dark cyberpunk theme
- IPC: multiproc msg passing btwn GUI+runner

## DIR STRUCT
```
pyprobe/
├── __main__.py          # CLI entry. --loglevel DEBUG for tracing
├── logging.py           # centralized logging. use get_logger(__name__)
├── state_tracer.py      # --trace-states for GUI state debugging
├── core/
│   ├── anchor.py        # ProbeAnchor: frozen dataclass, hashable
│   ├── runner.py        # subprocess runs target script w/ tracer
│   ├── tracer.py        # sys.settrace hook
│   └── data_classifier.py # classify captured values for plot routing
├── gui/
│   ├── main_window.py   # MainWindow: top-level UI, signal routing
│   ├── probe_controller.py # probe lifecycle, overlays, lens prefs
│   ├── message_handler.py  # IPC message processing
│   ├── script_runner.py    # script execution control
│   ├── code_viewer.py      # CodeViewer: probe click detection
│   ├── probe_panel.py      # ProbePanel: per-variable display
│   ├── panel_container.py  # grid layout for panels
│   ├── layout_manager.py   # maximize/restore, dock bar integration
│   ├── focus_manager.py    # panel focus tracking
│   ├── dock_bar.py         # parked panel tabs
│   ├── probe_registry.py   # central probe state mgmt
│   ├── drag_helpers.py     # MIME encode/decode for overlay drops
│   └── ...
├── plugins/
│   ├── base.py          # PlotPlugin ABC
│   ├── registry.py      # plugin discovery/registration
│   └── builtins/        # waveform.py, constellation.py, scalar.py
├── plots/
│   ├── plot_factory.py  # routes dtype→plugin
│   ├── axis_controller.py # axis pinning/editing
│   └── ...
├── analysis/
│   ├── ast_locator.py   # cursor→var mapping
│   └── anchor_mapper.py # maps anchors across file edits
└── ipc/
    ├── channels.py      # IPCChannel: queue-based comm
    └── messages.py      # Message types
```

## KEY DOCS
- `plans/implementation/m1/README.md` - M1 milestone overview
- `plans/plan.md` - full impl details
- `CONSTITUTION.md` - proj philosophy
- `prompts/END.md` - lesson entry format
- `.agent/BACKLOG.md` - bugs + features (priority-sorted)

## DEBUG
```bash
python -m pyprobe --loglevel DEBUG examples/dsp_demo.py
# logs → /tmp/pyprobe_debug.log
```

### Capture Timing Trace
For debugging probe capture timing (deferred captures, LHS/RHS, multi-line statements):
```bash
PYPROBE_TRACE=1 python -m pyprobe examples/dsp_demo.py
```
Prints detailed `[TRACE]` output to stdout showing:
- `DEFER` - when deferred capture is registered
- `_flush_deferred` - flush decisions, object ID tracking
- `CAPTURE` - actual capture with array mean for complex data
- `AnchorMatcher.match` - anchor matching with is_assignment status
- `ASTLocator` - LHS detection for line 72 variables (hardcoded for dsp_demo debugging)

## LESSONS (STAR-AR FORMAT)
> see `prompts/END.md` for format spec

### PROCESS LESSONS (debugging approach)

#### L10 2026-02-07 debug-observe-first
S: GUI button stuck at PAUSE after script end
T: fix button state bug
A: hypothesized causes, made code changes, tested → repeated 4x
R: wasted effort, wrong hypotheses, no progress
A': add comprehensive state tracing FIRST, observe actual behavior
R': trace reveals exact failure point
Fix: created state_tracer.py with --trace-states flag

#### L11 2026-02-07 gui-debug-pattern
S: intermittent GUI state bug
A: read code, guess root cause, patch speculatively
R: multiple failed fixes
A': instrument (State, Action) → (NewState) at every transition
Fix: trace every IPC msg, button click, state change; log to file

#### L12 2026-02-07 ipc-debug-both-sides
S: msg sent but never received
A: added logging only on receiver (GUI) side
R: couldn't see if msg was actually sent
A': log on BOTH sender (subprocess) AND receiver (GUI)
Fix: print to sys.__stderr__ in subprocess, trace in GUI

#### L13 2026-02-08 gui-debug-user-interaction
S: debugging GUI app with trace logging added
A: launched `python -m pyprobe ...` repeatedly, waited for cmd completion
R: GUI never completes, no output until user interaction
A': ask user to: 1) launch, 2) interact, 3) share terminal output

### DESIGN LESSONS (architecture/philosophy)

#### L3 2026-02-06 filter-vs-degrade
S: non-data symbols (np, print) probed by user
A: block probing in `_get_anchor_at_position()` → return None
R: also blocked func args like `x` in `foo(x)`, valid use case
A': allow all probes, show "Nothing to show" placeholder
Fix: graceful degradation > strict filtering

#### L6 2026-02-06 anchor-sync
S: probing `x` and `wfm` on same line → time async
A: each anchor checks throttle independently
R: jitter, graphs drift out of phase
A': shared throttle per (file, line) location
Fix: `_location_throttle` dict in tracer

#### L7 2026-02-06 tracer-pre-exec
S: probing assignment `wfm = Waveform(...)`
A: capture on 'line' event
R: trace event is PRE-exec, captured old value
A': defer capture to NEXT event in same scope
Fix: `is_assignment` flag + `_pending_deferred` buffer

#### L8 2026-02-07 scalar-sort-order
S: waveform collection scalars [t0, dt] need semantic order
A: sorted scalars by value `scalars.sort()`
R: t0=10, dt=0.2 → sorted to [0.2, 10], broke time vector
A': identify t0/dt by attr name patterns, never sort by value
Fix: `_classify_as_waveform()` detects t0/dt patterns

## PATTERNS

### DEBUG-FIRST-PATTERNS (CRITICAL - from L10, L11, L12)
For complex/intermittent bugs, DO NOT hypothesize before observing:

```
1. GUI state bugs → add state tracer FIRST
   python -m pyprobe --trace-states <script>
   
2. IPC issues → log BOTH sides
   subprocess: print(..., file=sys.__stderr__)
   GUI: tracer.trace_ipc_received(...)
   
3. State machine bugs → trace (State, Action) → (NewState)
   - every button click
   - every IPC message
   - every state change
   
4. Only hypothesize AFTER trace shows exact failure point
```

### logging pattern
```python
from pyprobe.logging import get_logger
logger = get_logger(__name__)
logger.debug("msg")
```

### signal-slot probe flow
1. CodeViewer.mousePressEvent → checks `anchor in _active_probes`
2. if active: emits `probe_removed(anchor)`
3. if not: emits `probe_requested(anchor)`
4. MainWindow slots handle: `_on_probe_requested`, `_on_probe_remove_requested`
5. removal uses anim callback for deferred cleanup

### PyQt anim pattern (CRITICAL)
```python
# ALWAYS do both:
anim = QPropertyAnimation(effect, b"opacity", widget)  # parent to widget
widget._fade_anim = anim  # store ref
anim.start()
```

### running python (MANDATORY)
```bash
# ALWAYS activate venv before running python:
source /Users/ppal/repos/pyprobe/.venv/bin/activate && python -m pyprobe ...
```

## GOTCHAS
- ProbeAnchor immutable, can't modify after creation
- animations.py: MUST parent QPropertyAnimation to prevent GC
- code_viewer._active_probes must stay in sync w/ main_window._probe_panels
- IPC msgs are dict-serialized, anchor.to_dict() / ProbeAnchor.from_dict()
- func sig w/ defaults: always use kwargs for optional args after first
- QPlainTextEdit defaults to word wrap ON, breaks `col * char_width` math
- custom objects can't pickle across IPC, serialize in tracer._serialize_value()
- mp.Queue.put() uses feeder thread; os._exit() kills it mid-send → sleep before exit
- drag-drop MIME: ALL anchor fields must be encoded/decoded (is_assignment was missing)
- overlay matching: must compare full anchor identity (symbol+line+is_assignment), not just symbol name
- deferred capture in loops: must track object ID, var_exists alone triggers on stale value from prev iteration
- QScrollArea.layout() returns None; panels are in widget().layout()
- QGridLayout.itemAt() has gaps; iterate _panels dict not layout for reliable widget access

## INVARIANTS TO CHECK
- [ ] Qt obj lifetime: parent set? ref stored?
- [ ] func calls: kwargs for optional params?
- [ ] dict keys: using hashable frozen obj?
- [ ] callbacks: will obj exist when callback fires?
- [ ] python cmds: activated .venv first?

## UPDATE PROTOCOL
1. **Bug fixed?** → `@[prompts/END.md]` → add STAR-AR entry
2. **Pattern found?** → add to PATTERNS section
3. **Non-obvious behavior?** → add to GOTCHAS
4. **New important file?** → update DIR STRUCT
5. **Invariant violated?** → add to INVARIANTS TO CHECK
6. **Fixed bug/feature?** → DELETE from BACKLOG.md (don't strikethrough)
