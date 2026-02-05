# PyProbe Vision & Roadmap
## Claude's Take

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

**PyProbe = Python's oscilloscope**

- Code in VS Code
- Probe in PyProbe
- Click line → see signal
- No print(). No plt.show()

---

## Target Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     GUI PROCESS                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ File Tree   │  │ Code View   │  │ Probe Panels    │  │
│  │ (read-only) │  │ (click→probe│  │ (tabbed groups) │  │
│  └──────┬──────┘  └──────┬──────┘  └────────▲────────┘  │
│         │                │                   │           │
│         └────────┬───────┘                   │           │
│                  ▼                           │           │
│         ┌───────────────┐           ┌───────┴────────┐  │
│         │ ProbeRegistry │           │ PluginManager  │  │
│         │ (anchors)     │           │ (visualizers)  │  │
│         └───────┬───────┘           └────────────────┘  │
└─────────────────┼────────────────────────────────────────┘
                  │ IPC (cmds)
                  ▼
┌──────────────────────────────────────────────────────────┐
│                   RUNNER PROCESS                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │                   Tracer v2                          ││
│  │  ┌──────────────┐    ┌─────────────────────────┐    ││
│  │  │ AnchorMatcher│    │ RingBuffer (per anchor) │    ││
│  │  │ file:line:var│    │ [v0][v1][v2]...[vN]     │    ││
│  │  └──────────────┘    └─────────────────────────┘    ││
│  └─────────────────────────────────────────────────────┘│
│                          │                               │
│                          ▼ IPC (data)                    │
└──────────────────────────────────────────────────────────┘
```

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

## Milestones

### M1: Source-Anchored Probing
**Code is the UI. Hover to reveal. Click to probe.**

No [+] buttons. Visual noise. Breaks code density.
Instead: **Active Text** - variables are clickable wires.

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

**Tasks:**
- [ ] Add `ProbeAnchor` dataclass to `messages.py` (with col)
- [ ] Refactor `VariableTracer` to match `(file, line, symbol)`
- [ ] Build `CodeViewer` (QPlainTextEdit subclass)
  - [ ] `setMouseTracking(True)`
  - [ ] `cursorForPosition(pos)` → get text under mouse
  - [ ] Connect to AST locator for var detection
- [ ] Build `ASTLocator` - map (line, col) → ast.Name node
- [ ] `QSyntaxHighlighter` for hover glow + probe highlights
- [ ] Gutter widget with 👁 icon painting
- [ ] Color manager: assign colors to probes, sync to plots
- [ ] Wire click → `CMD_ADD_WATCH(anchor)`
- [ ] Update `WatchConfig` to use anchor
- [ ] Update IPC payload to include anchor

**Key files:**
- `pyprobe/ipc/messages.py` - ProbeAnchor dataclass
- `pyprobe/core/tracer.py` - anchor matching in trace func
- `pyprobe/gui/code_viewer.py` - NEW (complex: mouse tracking)
- `pyprobe/gui/code_gutter.py` - NEW (eye icon painting)
- `pyprobe/analysis/ast_locator.py` - NEW (cursor → var)
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
Right-click probe → View As...
  ├─ Waveform (default for real[])
  ├─ Constellation (default for complex[])
  ├─ Spectrum (FFT magnitude)
  ├─ IQ (real/imag split)
  ├─ Histogram
  └─ Custom...
```

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

**Tasks:**
- [ ] Define `ProbePlugin` ABC in `pyprobe/plugins/base.py`
- [ ] Refactor existing plots to implement plugin API
- [ ] Add `PluginRegistry` with auto-discovery
- [ ] Add context menu "View As..." on probe panels
- [ ] Add `SpectrumPlot` plugin (FFT)
- [ ] Add `IQPlot` plugin (split real/imag)
- [ ] Add `HistogramPlot` plugin

**Key files:**
- `pyprobe/plugins/base.py` - NEW
- `pyprobe/plugins/registry.py` - NEW
- `pyprobe/plots/*.py` - refactor to plugins
- `pyprobe/gui/probe_panel.py` - context menu

---

### M3: Probe Groups & Tabs
**Tame the chaos.**

```
┌─────────────────────────────────────────────┐
│ [TX Chain] [RX Chain] [Metrics] [+]         │  ← tabs
├─────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ tx_sig  │ │ tx_filt │ │ tx_out  │       │
│  └─────────┘ └─────────┘ └─────────┘       │
└─────────────────────────────────────────────┘
```

**Tasks:**
- [ ] Add `ProbeGroup` dataclass
- [ ] Replace single probe area with `QTabWidget`
- [ ] Drag-drop probes between tabs
- [ ] Save/load group layouts (JSON)
- [ ] Auto-group by file or function (optional)

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
│ ◀ ■ ▶   [====●=====] Frame 1247/2000       │  ← scrubber
│         ↑ current position                  │
└─────────────────────────────────────────────┘
```

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

**Tasks:**
- [ ] Implement `RingBuffer` class with shm backend
- [ ] Tracer writes to ring buffer (not queue)
- [ ] GUI reads from ring buffer at 60Hz
- [ ] Add scrubber widget to probe panel
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
source    plugins   tabs      DVR       files
anchor
         ▲
         │ foundation - must be solid
```

**Why this order:**
1. M1 = foundation. Everything else builds on anchors.
2. M2 = quick win after M1. Reuses existing plots.
3. M3 = UX polish. Makes tool usable at scale.
4. M4 = differentiator. Killer feature.
5. M5 = completeness. Professional feel.

---

## What NOT to Build

| Temptation | Why avoid |
|------------|-----------|
| VS Code extension | Complexity. PyProbe standalone is enough. |
| Edit code in PyProbe | Scope creep. Use real editor. |
| Breakpoints/stepping | Not a debugger. Continuous observation. |
| Remote debugging | Later. Local first. |
| Web UI | PyQt is faster for 60fps plots. |

---

## Verification Plan

### M1 Test
```bash
python -m pyprobe examples/dsp_demo.py
# 1. See code viewer with dsp_demo.py loaded
# 2. Hover over `received_symbols` → var glows
# 3. Click it → probe created, var turns colored
# 4. Eye icon appears in gutter
# 5. Run script
# 6. Plot updates live, color matches text highlight
```

### M2 Test
```bash
# 1. Probe a complex array
# 2. Right-click → View As → Spectrum
# 3. FFT plot appears
# 4. Data still flows
```

### M3 Test
```bash
# 1. Create 10 probes
# 2. Drag into groups: TX, RX
# 3. Switch tabs
# 4. Restart script
# 5. Groups persist
```

### M4 Test
```bash
# 1. Run script to completion
# 2. Script ends
# 3. Scrub slider back
# 4. See historical values
# 5. Probe still works
```

---

## Summary

| Milestone | Tagline | Core Change |
|-----------|---------|-------------|
| M1 | Click to probe | ProbeAnchor replaces var name |
| M2 | One var, many views | Plugin API |
| M3 | Tame the chaos | Tabbed groups |
| M4 | Probe the past | Ring buffer + scrubber |
| M5 | Full project | File tree + multi-file |

**North star:** Make Python DSP debugging feel like LabVIEW.
