# PYPROBE AI README
> AI-optmzd doc. No prose. Max density. Update on every lesson lrnd.

## FIRST: READ THIS
1. Check LESSONS section before debugging - may already be solved
2. After fixing bug → run `@[prompts/SESSION-END.md]` to log lesson
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
    └── SESSION-END.md  # STAR-AR lesson format
```

## KEY DOCS
- `plans/implementation/m1/README.md` - M1 milestone overview
- `plans/plan.md` - full impl details
- `CONSTITUTION.md` - proj philosophy
- `prompts/SESSION-END.md` - lesson entry format
- `.agent/FEATURES.md` - planned features (priority-sorted)
- `.agent/BUGS.md` - bug backlog

## DEBUG
```bash
python -m pyprobe --loglevel DEBUG examples/dsp_demo.py
# logs → /tmp/pyprobe_debug.log
```

## LESSONS (STAR-AR FORMAT)
> see `prompts/SESSION-END.md` for format spec

### L1 2026-02-06 anim-GC
S: fade_out anim on probe removal
T: animate UI cleanup
A: created QPropertyAnimation w/o parent/ref
R: anim GC'd, callback never fires
A': parent anim to widget + store ref
R': anim completes, cleanup runs
Fix: `widget._fade_anim = anim; parent=widget`
File: gui/animations.py

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
R: still broken, wrong hypothesis
A': verify assumptions (is word wrap on?) before fixing
R': find actual root cause
Fix: question defaults before adding offsets
File: gui/code_viewer.py

## PATTERNS

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

## GOTCHAS
- ProbeAnchor immutable, can't modify after creation
- animations.py: MUST parent QPropertyAnimation to prevent GC
- code_viewer._active_probes must stay in sync w/ main_window._probe_panels
- IPC msgs are dict-serialized, anchor.to_dict() / ProbeAnchor.from_dict()
- func sig w/ defaults: always use kwargs for optional args after first
- QPlainTextEdit defaults to word wrap ON, breaks `col * char_width` math

## INVARIANTS TO CHECK
- [ ] Qt obj lifetime: parent set? ref stored?
- [ ] func calls: kwargs for optional params?
- [ ] dict keys: using hashable frozen obj?
- [ ] callbacks: will obj exist when callback fires?

## UPDATE PROTOCOL
1. **Bug fixed?** → `@[prompts/SESSION-END.md]` → add STAR-AR entry
2. **Pattern found?** → add to PATTERNS section
3. **Non-obvious behavior?** → add to GOTCHAS
4. **New important file?** → update DIR STRUCT
5. **Invariant violated?** → add to INVARIANTS TO CHECK
6. **Fixed bug/feature?** → DELETE from BUGS.md/FEATURES.md (don't strikethrough)

