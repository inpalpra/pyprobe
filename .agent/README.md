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
├── __main__.py      # CLI entry. --loglevel DEBUG for tracing
├── logging.py       # centralized logging. use get_logger(__name__)
├── core/
│   ├── anchor.py    # ProbeAnchor: frozen dataclass, hashable, dict key OK
│   ├── runner.py    # subprocess runs target script w/ tracer
│   └── tracer.py    # sys.settrace hook
├── gui/
│   ├── main_window.py   # MainWindow: probe lifecycle, IPC polling
│   ├── code_viewer.py   # CodeViewer: click detection, probe_requested/probe_removed signals
│   ├── animations.py    # ProbeAnimations: fade_in/fade_out
│   ├── probe_registry.py # ProbeRegistry: central probe state mgmt
│   ├── probe_panel.py   # ProbePanel + ProbePanelContainer
│   └── ...
├── analysis/
│   ├── ast_locator.py   # ASTLocator: cursor→var mapping
│   └── anchor_mapper.py # maps anchors across file edits
├── ipc/
│   ├── channels.py      # IPCChannel: queue-based comm
│   └── messages.py      # Message types
└── prompts/             # AI prompt templates
    └── END.md  # STAR-AR lesson format
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

## LESSONS (STAR-AR FORMAT)
> see `prompts/END.md` for format spec

### L1 2026-02-06 anim-GC
S: fade_out anim on probe removal
T: animate UI cleanup
A: created QPropertyAnimation w/o parent/ref
R: anim GC'd, callback never fires
A': parent anim to widget + store ref
R': anim completes, cleanup runs
Fix: `widget._fade_anim = anim; parent=widget`
File: gui/animations.py

### L9 2026-02-07 queue-feeder-race
S: subprocess sends DATA_SCRIPT_END, then os._exit()
T: signal script completion to GUI
A: queue.put() + os._exit() immediately
R: feeder thread killed mid-send, msg lost, GUI stuck at PAUSE
A': sleep 100ms before os._exit() to let feeder complete
R': msg reliably arrives at GUI
Fix: `time.sleep(0.1)` before `os._exit(exit_code)`
File: core/runner.py:344-347

### L10 2026-02-07 debug-observe-first
S: GUI button stuck at PAUSE after script end
T: fix button state bug
A: hypothesized causes, made code changes, tested → repeated 4x
R: wasted effort, wrong hypotheses, no progress
A': add comprehensive state tracing FIRST, observe actual behavior
R': trace reveals exact failure point (DATA_SCRIPT_END never received)
Fix: created state_tracer.py with --trace-states flag
File: pyprobe/state_tracer.py

### L11 2026-02-07 gui-debug-pattern
S: intermittent GUI state bug
T: debug state machine logic
A: read code, guess root cause, patch speculatively
R: multiple failed fixes, user frustration
A': instrument (State, Action) → (NewState) at every transition
R': trace log pinpoints exact broken transition
Fix: trace every IPC msg, button click, state change; log to file
File: state_tracer.py, main_window.py

### L12 2026-02-07 ipc-debug-both-sides
S: msg sent but never received
T: find where msg is lost
A: added logging only on receiver (GUI) side
R: couldn't see if msg was actually sent
A': log on BOTH sender (subprocess) AND receiver (GUI)
R': terminal shows "sent successfully" but trace shows not received → queue issue
Fix: print to sys.__stderr__ in subprocess, trace in GUI
File: runner.py, main_window.py

### L13 2026-02-08 gui-debug-user-interaction
S: debugging GUI app with trace logging added to code
T: observe trace output to understand bug
A: launched `python -m pyprobe ...` repeatedly, waited for cmd completion
R: GUI never completes, no output until user clicks to trigger code path, wasted time
A': ask user to launch GUI, interact (click probe target), then share terminal output
R': debug output appears after user triggers code path, useful data obtained
Fix: for PyProbe GUI debugging, always instruct user to: 1) launch, 2) click to trigger, 3) share output
File: process


### L2 2026-02-06 kwarg-order
S: calling fade_out w/ callback
T: trigger cleanup after anim
A: `fade_out(panel, callback)` positional
R: callback passed as duration_ms, TypeError
A': check func sig, use kwarg `on_finished=`
R': correct arg binding
Fix: `fade_out(panel, on_finished=callback)`
File: gui/main_window.py:385

### L3 2026-02-06 filter-vs-degrade
S: non-data symbols (np, print) probed by user
T: prevent meaningless probes
A: block probing in `_get_anchor_at_position()` → return None
R: also blocked func args like `x` in `foo(x)`, valid use case
A': allow all probes, show "Nothing to show" placeholder
R': graceful UX, no false negatives
Fix: remove `is_probeable()` check; add placeholder in ScalarDisplay
File: gui/code_viewer.py, plots/scalar_display.py

### L4 2026-02-06 word-wrap-default
S: highlight rects misplaced when window resized
T: calculate variable rect from line/col position
A: `col_start * char_width` assumed no wrap
R: rects in wrong place when text wraps to next visual line
A': check QPlainTextEdit defaults, disable wrap for code viewer
R': rects stay aligned regardless of window size
Fix: `self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)`
File: gui/code_viewer.py:67

### L5 2026-02-06 symptom-vs-root
S: highlight rects misplaced when window resized
T: fix positioning bug
A: add `documentMargin()` to x-offset (symptom-based fix)
R: fixed specific case, but root cause was wrap mode
Fix: see L4 (root cause fix)
File: gui/code_viewer.py

### L6 2026-02-06 anchor-sync
S: probing `x` and `wfm` on same line -> time async
T: capture related vars at exact same time
A: each anchor checks throttle independently
R: jitter, graphs drift out of phase
A': shared throttle per (file, line) location
R': all anchors on line capture atomic snapshot
Fix: `_location_throttle` dict in tracer
File: core/tracer.py

### L7 2026-02-06 tracer-pre-exec
S: probing assignment `wfm = Waveform(...)`
T: capture result of assignment
A: capture on 'line' event
R: trace event is PRE-exec, captured old value (frame N-1)
A': defer capture to NEXT event in same scope (ignore 'call')
R': captures post-exec value (frame N)
Fix: `is_assignment` flag + `_pending_deferred` buffer
File: core/tracer.py
R: still broken, wrong hypothesis
A': verify assumptions (is word wrap on?) before fixing
R': find actual root cause
Fix: question defaults before adding offsets
File: gui/code_viewer.py

### L6 2026-02-06 venv-run
S: running `python -m pyprobe` for verification
T: test new ScalarHistoryChart feature
A: ran `python -m pyprobe` without activating venv
R: ModuleNotFoundError: No module named 'PyQt6'
A': always activate proj venv before running
R': all deps available
Fix: `source .venv/bin/activate && python -m pyprobe ...`
File: (all python cmds)

### L7 2026-02-06 ipc-pickle-custom
S: probing custom Waveform object (user-defined class)
T: display waveform with proper time axis
A: sent custom object through multiprocessing queue
R: `PicklingError: Can't pickle <class '__main__.Waveform'>`
A': serialize to dict before IPC, deserialize on GUI side
R': waveform plots correctly with time axis
Fix: `_serialize_value()` in tracer converts to `{'__waveform__': True, 'x': ..., 't': ...}`
File: core/tracer.py, plots/waveform_plot.py, core/data_classifier.py

### L8 2026-02-07 scalar-sort-order
S: waveform collection scalars [t0, dt] need semantic order
T: serialize waveform scalars for IPC
A: sorted scalars by value `scalars.sort()`
R: t0=10, dt=0.2 → sorted to [0.2, 10], broke time vector calc
A': identify t0/dt by attr name patterns, never sort by value
R': t0 preserved at idx 0, dt at idx 1, time vector correct
Fix: `_classify_as_waveform()` detects t0/dt patterns → order [t0,dt]; removed `.sort()`
File: core/data_classifier.py:115-145, core/tracer.py:267,287

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
