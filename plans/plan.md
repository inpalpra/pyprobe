# PyProbe Vision & Roadmap
## Claude's Take

---

## Non-Negotiable UX Principles

| Principle | Meaning |
|-----------|---------|
| Probing is a gesture | Not a configuration step. Touch the signal. |
| Single-action | Hover → click. No dialogs. |
| Symmetric removal | Click again to remove. |
| Code view is truth | Not a watch list. Probes visible in code first. |
| Live, not sequential | No load → configure → run mental model. |

**Interface IS the product.** Every downstream decision must pass: *does this feel like a single gesture?*

---

## Pain Summary

| Pain | Why it hurts |
|------|--------------|
| Type var names | friction. LabVIEW = click |
| Same name, diff place | `x` in foo() != `x` in bar() |
| Complex = constellation | sometimes want spectrum, IQ |
| 20 probes = chaos | no tabs, no groups |
| Run ends = data gone | can't probe history |
| Multi-file weak | sub-modules second-class |

---

## Core Insight

**Variable names are aliases. Locations are identity.**

```
BAD:  probe("x")           # which x?
GOOD: probe(file:42, "x")  # THIS x
```

---

## Vision

**PyProbe = Python's Live Oscilloscope**

PyProbe is reactive:
- Code changes are reflected immediately.
- Probes can be added or removed while the script is running.
- New probes begin updating in the same or next frame.
- No restarts. No static setup. Always live.

Core experience:
- Code in editor (any editor)
- Probe in PyProbe
- Click line → see signal
- No print(). No plt.show()

---

## Target Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     GUI PROCESS                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐       │
│  │ File Tree   │  │ Code View   │  │ Probe Panels    │       │
│  │ (read-only) │  │ (click→probe│  │ (auto-grouped)  │       │
│  └──────┬──────┘  └──────┬──────┘  └────────▲────────┘       │
│         │                │                   │                │
│         └────────┬───────┘                   │                │
│                  ▼                           │                │
│         ┌───────────────┐           ┌───────┴────────┐       │
│         │ ProbeRegistry │           │ PluginManager  │       │
│         │ (UX contract) │           │ (visualizers)  │       │
│         └───────┬───────┘           └────────────────┘       │
└─────────────────┼────────────────────────────────────────────┘
                  │ IPC (cmds)
                  ▼
┌──────────────────────────────────────────────────────────────┐
│                   RUNNER PROCESS                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                   Tracer v2                              │ │
│  │  ┌──────────────┐    ┌─────────────────────────┐        │ │
│  │  │ AnchorMatcher│    │ RingBuffer (per anchor) │        │ │
│  │  │ file:line:var│    │ [v0][v1][v2]...[vN]     │        │ │
│  │  └──────────────┘    └─────────────────────────┘        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          │                                    │
│                          ▼ IPC (data)                         │
└──────────────────────────────────────────────────────────────┘
```

**Architecture note:** IPC-first design. GUI host can change later (standalone → VS Code → other). Core UX model has no editor-specific assumptions.

---

## Data Model (Foundation)

### ProbeAnchor (immutable identity)
```python
@dataclass(frozen=True)
class ProbeAnchor:
    file: str      # abs path
    line: int      # 1-indexed
    col: int       # column offset (disambiguates x = x + 1)
    symbol: str    # var name at that location
    func: str = "" # enclosing function (optional)
```

### ProbeRegistry (UX contract)

`ProbeRegistry` is not just a data structure. It represents:
- **User intent** — what the user wants to observe
- **Probe lifecycle** — active, invalidated, removed
- **Visual state** — colors, grouping, panel assignment

Every mutation to `ProbeRegistry` has immediate UX consequences.

### Why frozen?
- hashable → use as dict key
- stable → survives code edits (mostly)
- unique → no ambiguity

### Why col?
- `z = y * h` → click y vs z = different probes
- same line, diff column = diff anchor

### Current vs New

| Today | Tomorrow |
|-------|----------|
| `watches: Dict[str, WatchConfig]` | `watches: Dict[ProbeAnchor, WatchConfig]` |
| `CMD_ADD_WATCH(name)` | `CMD_ADD_WATCH(anchor)` |
| ambiguous | precise |

---

## UX Smell Test

Every feature must pass:

- [ ] Can I probe this without stopping the program?
- [ ] Can I undo the probe instantly?
- [ ] Can I see probe state directly in code?
- [ ] Can I understand probe layout without reading a list?
- [ ] Does this feel like touching a signal, not configuring a tool?

> **Note:** Each milestone's UX Acceptance Criteria operationalize these principles for that specific feature set.

---

## Definition of Done

Each milestone includes **UX Acceptance Criteria** — behavioral tests that must ALL pass before the milestone is considered complete. These are not implementation tasks; they are the user-experience bar that implementation must achieve.

**Criteria categories:**
- **Behavioral criteria** — observable user interactions that must work exactly as specified
- **Mental Model Check** — the subjective "feel" test (every milestone ends with one)

❌ **If any checkbox fails, the milestone is not complete.**

---

## Milestones

### M1: Source-Anchored Probing
**Code is the UI. Hover to reveal. Click to probe.**

No [+] buttons. Visual noise. Breaks code density.
Instead: **Active Text** - variables are clickable wires.

#### UX Contract

**Hot-Probing:**
- Probes can be added/removed while the script is running.
- No restart required to observe new signals.
- New probes begin updating in the same or next frame.

**Live Source Sync:**
- Code view auto-reloads on file save (filesystem-driven, editor-agnostic).
- Existing probe anchors preserved on best-effort basis.
- Invalidated anchors are visually marked and stop updating (no silent failure).

#### Interaction Semantics

**Click toggles probe state:**
- Absent → add probe
- Present → remove probe

**Hover behavior:**
- Cursor snaps to nearest valid probe target.
- Prefer LHS symbols when ambiguous (`x = x + 1` → LHS `x`).
- If no valid target, show nothing (no warning UI).

#### Visual States

```
STATE 1: Clean (no mouse)
┌───┬─────────────────────────┐
│   │ 10: t = np.arange(100)  │
│   │ 11: x = np.sin(t)       │
│   │ 12: z = y * h           │
└───┴─────────────────────────┘

STATE 2: Hover (mouse over line 12, near 'y')
┌───┬─────────────────────────┐
│   │ 12: z = [y] * h         │  ← 'y' glows, clickable
└───┴─────────────────────────┘

STATE 3: Click (probed z=cyan, y=magenta)
┌───┬─────────────────────────┐
│ 👁 │ 12: [z] = [y] * h       │  ← z=cyan bg, y=magenta bg
└───┴─────────────────────────┘
     Eye = "something probed here"
     Colors = match plot colors
```

#### Gutter Semantics

The gutter is not decorative. It answers:
> "Where in this file does signal observation occur?"

- 👁 icons indicate authoritative probe locations.
- Scan gutter to find all probed lines instantly.
- Color highlighting in code matches plot colors exactly.

**Hybrid UI:**
- 👁 in gutter → scannability (scroll fast, spot probes)
- Color highlight on text → precision (which var exactly)
- Color sync → plot1=cyan, var text=cyan bg

**Data model update:**
```python
@dataclass(frozen=True)
class ProbeAnchor:
    file: str      # abs path
    line: int      # 1-indexed
    col: int       # column offset (for multi-var lines)
    symbol: str    # var name
    func: str = "" # enclosing function
```

#### UX Acceptance Criteria

> **All criteria must pass for M1 to be considered complete.**

**Probe Gesture**
- [ ] I can add a probe with a single click on a variable
- [ ] I can remove the same probe by clicking it again
- [ ] No dialogs, menus, or configuration steps are required
- [ ] I never have to type a variable name to probe it

**Liveness**
- [ ] I can add or remove probes while the script is running
- [ ] A newly added probe starts updating in the same or next frame
- [ ] No restart is required to observe a new signal

**Code Trust**
- [ ] The code view always reflects the latest saved file
- [ ] If the file changes on disk, the view updates automatically
- [ ] If a probe anchor becomes invalid, it is visually marked
- [ ] Invalid probes never show stale or misleading data

**Discoverability**
- [ ] I can scroll through a file and instantly see where probes exist
- [ ] Gutter icons make probe locations obvious at a glance
- [ ] Hovering over code never shows confusing or noisy UI states
- [ ] If no probeable symbol exists under the cursor, nothing happens

**Precision**
- [ ] Clicking `x` in `x = x + 1` probes the intended symbol
- [ ] Multiple symbols on the same line are disambiguated reliably
- [ ] The probed symbol is visually unambiguous in the code

**Mental Model Check**
- [ ] Probing feels like touching a wire, not setting up a watch
- [ ] I do not think about "configuration" at any point
- [ ] I trust what I see without second-guessing

❌ If any box fails, M1 is not complete.

**Tasks:**
- [ ] Add `ProbeAnchor` dataclass to `messages.py` (with col)
- [ ] Refactor `VariableTracer` to match `(file, line, symbol)`
- [ ] Build `CodeViewer` (QPlainTextEdit subclass)
  - [ ] `setMouseTracking(True)`
  - [ ] `cursorForPosition(pos)` → get text under mouse
  - [ ] Connect to AST locator for var detection
  - [ ] Filesystem watcher for auto-reload on save
  - [ ] Anchor preservation logic on reload
  - [ ] Invalidated anchor visual state (grayed, no updates)
- [ ] Build `ASTLocator` - map (line, col) → ast.Name node
  - [ ] LHS preference for ambiguous positions
- [ ] `QSyntaxHighlighter` for hover glow + probe highlights
- [ ] Gutter widget with 👁 icon painting
- [ ] Color manager: assign colors to probes, sync to plots
- [ ] Wire click → toggle probe state (add if absent, remove if present)
- [ ] Hot-probe IPC: `CMD_ADD_WATCH` / `CMD_REMOVE_WATCH` while running
- [ ] Update `WatchConfig` to use anchor
- [ ] Update IPC payload to include anchor

**Key files:**
- `pyprobe/ipc/messages.py` - ProbeAnchor dataclass
- `pyprobe/core/tracer.py` - anchor matching in trace func, hot-add support
- `pyprobe/gui/code_viewer.py` - NEW (mouse tracking, file watching, reload)
- `pyprobe/gui/code_gutter.py` - NEW (eye icon painting)
- `pyprobe/analysis/ast_locator.py` - NEW (cursor → var, LHS preference)
- `pyprobe/gui/main_window.py` - layout change

**AST trick (column-aware):**
```python
def get_var_at_cursor(source: str, line: int, col: int) -> str | None:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if (node.lineno == line and
                node.col_offset <= col <= node.end_col_offset):
                return node.id
    return None
```

**Risks:**
| Risk | Mitigation |
|------|------------|
| `x = x + 1` (two x's) | col disambiguates. LHS default. |
| `obj.attr` | ast.Attribute node. Handle in M1.5. |
| `d['key']` | ast.Subscript. Defer to M1.5. |
| Dynamic code | AST = static only. Accept limitation. |

---

### M2: Plugin System (Lenses)
**One var, many views.**

```
Probe Panel Header:
┌─────────────────────────────────────────┐
│ rx_symbols @ line 42    [Constellation▾]│  ← lens dropdown
├─────────────────────────────────────────┤
│      ·  ·  ·                            │
│    ·   ·   ·                            │
│      ·  ·  ·                            │
└─────────────────────────────────────────┘
```

**Primary access:** Lens dropdown in probe panel header (always visible).
**Secondary access:** Right-click context menu (for discoverability).

Do not hide lens switching behind right-click only.

Available lenses:
- Waveform (default for real[])
- Constellation (default for complex[])
- Spectrum (FFT magnitude)
- IQ (real/imag split)
- Histogram
- Custom...

**Plugin API:**
```python
class ProbePlugin(ABC):
    name: str

    @abstractmethod
    def can_handle(self, dtype: str, shape: tuple) -> bool:
        """Return True if this plugin can visualize this data type"""

    @abstractmethod
    def create_widget(self) -> QWidget:
        """Return the plot widget"""

    @abstractmethod
    def update(self, value: Any, meta: dict) -> None:
        """Called with new data"""
```

#### UX Acceptance Criteria

> **All criteria must pass for M2 to be considered complete.**

**View Switching**
- [ ] I can change how a signal is visualized without re-probing it
- [ ] Switching views does not interrupt data flow
- [ ] The default view is always reasonable

**UI Friction**
- [ ] Common view switches do NOT require right-click
- [ ] Lens switching is discoverable without documentation
- [ ] Right-click menus are optional, not mandatory

**Consistency**
- [ ] Plot color remains consistent across all lenses
- [ ] The same probe identity is preserved across views
- [ ] Switching views never duplicates or loses probes

**Safety**
- [ ] Unsupported views are clearly disabled, not hidden
- [ ] I am never allowed to select a view that silently fails

**Mental Model Check**
- [ ] One signal, many lenses — not many probes
- [ ] Views feel like changing instruments, not re-wiring

❌ If any box fails, M2 is not complete.

**Tasks:**
- [ ] Define `ProbePlugin` ABC in `pyprobe/plugins/base.py`
- [ ] Refactor existing plots to implement plugin API
- [ ] Add `PluginRegistry` with auto-discovery
- [ ] Add lens dropdown to probe panel header (primary access)
- [ ] Add context menu "View As..." on probe panels (secondary access)
- [ ] Add `SpectrumPlot` plugin (FFT)
- [ ] Add `IQPlot` plugin (split real/imag)
- [ ] Add `HistogramPlot` plugin

**Key files:**
- `pyprobe/plugins/base.py` - NEW
- `pyprobe/plugins/registry.py` - NEW
- `pyprobe/plots/*.py` - refactor to plugins
- `pyprobe/gui/probe_panel.py` - header with lens dropdown + context menu

---

### M3: Probe Groups & Tabs
**Structure is the default.**

```
┌─────────────────────────────────────────────┐
│ [main.py:process] [filters.py:lowpass] [+]  │  ← auto-generated tabs
├─────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐        │
│  │ tx_sig  │ │ tx_filt │ │ tx_out  │        │
│  └─────────┘ └─────────┘ └─────────┘        │
└─────────────────────────────────────────────┘
```

**Grouping philosophy:**
- Probes are **auto-grouped by default** using code context (file + function).
- Grouping should feel inevitable, not optional.
- Manual drag-drop is an **override**, not the baseline workflow.
- Rename tabs freely. Drag probes between tabs to override auto-grouping.

#### UX Acceptance Criteria

> **All criteria must pass for M3 to be considered complete.**

**Default Behavior**
- [ ] Probes are grouped automatically without user action
- [ ] Grouping reflects code structure (file + function)
- [ ] I never start in an ungrouped "pile of plots" state

**Override Capability**
- [ ] I can manually move probes between groups
- [ ] Manual overrides persist across runs
- [ ] Auto-grouping never fights manual intent

**Navigation**
- [ ] I can understand the probe layout at a glance
- [ ] Tab names clearly explain why probes are grouped
- [ ] Switching groups is instant and obvious

**Cognitive Load**
- [ ] I do not think "where should this go?" when probing
- [ ] The tool answers that question for me by default

**Mental Model Check**
- [ ] Grouping feels like a reflection of my code, not a UI chore
- [ ] I never feel punished for probing many signals

❌ If any box fails, M3 is not complete.

**Tasks:**
- [ ] Add `ProbeGroup` dataclass
- [ ] Replace single probe area with `QTabWidget`
- [ ] Auto-group probes by `anchor.file + anchor.func` on creation
- [ ] Drag-drop probes between tabs (manual override)
- [ ] Tab renaming
- [ ] Save/load group layouts (JSON)
- [ ] Visual indicator for manually-overridden grouping

**Key files:**
- `pyprobe/gui/probe_tabs.py` - NEW
- `pyprobe/gui/main_window.py` - layout
- `pyprobe/config/layouts.py` - NEW

---

### M4: Time Travel (DVR)
**Probe the past.**

```
┌─────────────────────────────────────────────┐
│ [Probe: rx_symbols @ line 42]               │
│ ┌─────────────────────────────────────────┐ │
│ │      ·  ·  ·                            │ │
│ │    ·   ·   ·    (constellation)         │ │
│ │      ·  ·  ·                            │ │
│ └─────────────────────────────────────────┘ │
│ ◀ ■ ▶   [====●=====] Frame 1247/2000        │  ← scrubber
│         ↑ always visible                    │
└─────────────────────────────────────────────┘
```

**Discoverability:**
- Scrubber is **always visible**, even before history exists.
- When no history: scrubber is disabled/grayed, shows "Frame 0/0".
- Disabled UI is preferable to hidden features.
- Time travel should feel like a natural extension, not an "advanced mode".

**Data structure: Ring buffer in shared memory**

```
┌─────────────────────────────────────────────┐
│ SharedMemory: pyprobe_ring_{anchor_hash}    │
├─────────────────────────────────────────────┤
│ Header (64 bytes):                          │
│   write_idx: uint32                         │
│   read_idx: uint32                          │
│   capacity: uint32                          │
│   item_size: uint32                         │
│   dtype: char[16]                           │
│   shape: uint32[4]                          │
├─────────────────────────────────────────────┤
│ Data region:                                │
│   [frame0][frame1][frame2]...[frameN]       │
│      ↑ circular write                       │
└─────────────────────────────────────────────┘
```

#### UX Acceptance Criteria

> **All criteria must pass for M4 to be considered complete.**

**Discoverability**
- [ ] Time navigation UI is visible even before it is usable
- [ ] Disabled state clearly communicates future capability
- [ ] I discover time travel without reading documentation

**Control**
- [ ] I can scrub backward and forward intuitively
- [ ] Scrubbing never changes probe identity or layout
- [ ] Live and historical modes are visually distinct

**Trust**
- [ ] Historical data never mutates or reorders
- [ ] I always know whether I am viewing live or past data
- [ ] Frame counters and position are explicit

**Performance Feel**
- [ ] Scrubbing feels immediate, not laggy
- [ ] Playback speed feels smooth and intentional

**Mental Model Check**
- [ ] This feels like a DVR, not a buffer dump
- [ ] I instinctively try to scrub — and it works

❌ If any box fails, M4 is not complete.

**Tasks:**
- [ ] Implement `RingBuffer` class with shm backend
- [ ] Tracer writes to ring buffer (not queue)
- [ ] GUI reads from ring buffer at 60Hz
- [ ] Add scrubber widget to probe panel (always visible)
- [ ] Disabled state when no history
- [ ] Pause/play controls per probe
- [ ] Frame counter display

**Key files:**
- `pyprobe/ipc/ring_buffer.py` - NEW
- `pyprobe/core/tracer.py` - write to ring
- `pyprobe/gui/scrubber.py` - NEW
- `pyprobe/gui/probe_panel.py` - integrate

**Memory math:**
- 1000 frames × 4KB avg = 4MB per probe
- 10 probes = 40MB
- Acceptable for DSP workloads

---

### M5: Multi-file Navigation
**Full project awareness.**

```
┌──────────────┬────────────────────────────────┐
│ File Tree    │ Code View                      │
│──────────────│────────────────────────────────│
│ ▼ src/       │ # filters.py                   │
│   main.py    │ def lowpass(x, fc):            │
│ ► filters.py │     y = convolve(x, h)         │  ← hover y, click to probe
│   utils.py   │     return y                   │
└──────────────┴────────────────────────────────┘
```

#### UX Acceptance Criteria

> **All criteria must pass for M5 to be considered complete.**

**Navigation**
- [ ] I can browse project files without leaving PyProbe
- [ ] Loading a file never breaks probe context
- [ ] Probes across files behave identically to same-file probes

**Context**
- [ ] Probes clearly indicate which file/function they belong to
- [ ] Grouping remains coherent across files
- [ ] Cross-file comparisons are visually obvious

**Scale**
- [ ] Large projects do not feel heavier than small ones
- [ ] I do not need to mentally track "which file I'm in"

**Mental Model Check**
- [ ] The project feels like one continuous signal graph
- [ ] File boundaries do not break my debugging flow

❌ If any box fails, M5 is not complete.

**Tasks:**
- [ ] Add `QTreeView` file browser
- [ ] Track all .py files in project
- [ ] Click file → load in code view
- [ ] Tracer: remove `target_files` restriction
- [ ] Anchor works across any file

**Key files:**
- `pyprobe/gui/file_tree.py` - NEW
- `pyprobe/gui/main_window.py` - layout

---

## Priority Order

```
M1 ─────► M2 ─────► M3 ─────► M4 ─────► M5
source    plugins   auto-     DVR       files
anchor    (lenses)  groups
         ▲
         │ foundation - must be solid
```

**Why this order:**
1. M1 = foundation. Everything else builds on anchors. Hot-probing is non-negotiable.
2. M2 = quick win after M1. Reuses existing plots. Visible lens control.
3. M3 = structure. Auto-grouping makes scale manageable by default.
4. M4 = differentiator. Always-visible scrubber. Natural extension.
5. M5 = completeness. Professional feel.

---

## What NOT to Build (Now)

| Temptation | Stance |
|------------|--------|
| VS Code extension | Standalone first to prove probing UX. Architecture is IPC-first, so UI host can change later. Not ruled out. |
| Edit code in PyProbe | Scope creep. Use real editor. |
| Breakpoints/stepping | Not a debugger. Continuous observation. |
| Remote debugging | Later. Local first. |
| Web UI | PyQt is faster for 60fps plots. |

---

## Manual Test Scripts

> Step-by-step procedures to verify acceptance criteria are met.

### M1 Test
```bash
python -m pyprobe examples/dsp_demo.py
# 1. See code viewer with dsp_demo.py loaded
# 2. Hover over `received_symbols` → var glows, snaps to target
# 3. Click it → probe created, var turns colored, eye in gutter
# 4. Click again → probe removed (symmetric)
# 5. Script is running
# 6. Click new variable → probe added without restart (hot-probe)
# 7. Edit dsp_demo.py in external editor, save
# 8. Code view reloads, existing probes preserved
# 9. Delete probed line → probe marked invalid, stops updating
```

### M2 Test
```bash
# 1. Probe a complex array
# 2. Click lens dropdown in panel header → select Spectrum
# 3. FFT plot appears
# 4. Data still flows
# 5. Right-click → View As... also works (secondary)
```

### M3 Test
```bash
# 1. Probe variables in main.py:process() and filters.py:lowpass()
# 2. Tabs auto-created: "main.py:process", "filters.py:lowpass"
# 3. Drag probe to different tab (override)
# 4. Restart script
# 5. Groups persist, overrides preserved
```

### M4 Test
```bash
# 1. Scrubber visible but disabled before run
# 2. Run script
# 3. Scrubber enables, shows frame count
# 4. Script ends
# 5. Scrub slider back
# 6. See historical values
```

---

## Summary

| Milestone | Tagline | Core Change |
|-----------|---------|-------------|
| M1 | Click to probe (live) | ProbeAnchor + hot-probing + toggle |
| M2 | One var, many views | Plugin API + visible lens control |
| M3 | Structure by default | Auto-grouping by code context |
| M4 | Probe the past | Ring buffer + always-visible scrubber |
| M5 | Full project | File tree + multi-file |

**North star:** Make Python DSP debugging feel like touching a live signal.
