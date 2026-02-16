# AI-Driven Structural GUI Testing — Architectural Plan

**Date:** 2026-02-11  
**Status:** Draft  
**Scope:** PyProbe PyQt6 desktop application

---

## Executive Summary

This plan defines a staged path from the current test infrastructure (ad-hoc QTest scripts, subprocess-based CLI E2E tests) to a **structured, AI-native GUI testing harness** for PyProbe.

The key architectural insight: **skip the "LLM writes raw QTest" phase entirely**. The codebase already has strong structural foundations — signal/slot architecture, a ProbeRegistry, a StateTracer, a FocusManager, and CLI automation hooks. The fastest path to value is building a thin introspection + action layer *first*, then having the LLM operate at that abstraction level from day one.

This is viable because:
1. PyQt6's QObject tree is fully introspectable at runtime.
2. PyProbe already uses signals/slots for all meaningful state transitions.
3. The StateTracer already captures `(State, Action) → (NewState, Reactions)` — the exact primitive an LLM needs for behavioral reasoning.
4. The CLI automation (`--auto-run`, `--auto-quit`, `--probe`) proves subprocess-based orchestration works.

**Where this becomes extremely powerful:**
- LLM generates *behavioral contracts* ("when user presses M on a focused panel, the panel should maximize and all others should hide"), then the harness validates them deterministically.
- Zero visual testing. Pure structural + event-driven assertions.
- The LLM can iterate: introspect → hypothesize → simulate → observe → refine.

**Where this could fail:**
- `objectName` coverage is currently minimal (~10 widgets). Without robust naming, tree traversal is fragile.
- pyqtgraph widgets have their own internal structure that doesn't follow standard QWidget patterns.
- Timing-sensitive interactions (animations, throttled redraws) require careful handling.
- Signal/slot connections are not easily discoverable at runtime without MOC metadata hacking.

---

## Current State Assessment

### What Exists

| Asset | Status | Notes |
|-------|--------|-------|
| `StateTracer` | ✅ Production | Logs `(State, Action) → (NewState, Reactions)` to `/tmp/pyprobe_state_trace.log` |
| `ProbeRegistry` | ✅ Production | Central probe lifecycle with state machine (ARMED→LIVE→STALE→INVALID) |
| `FocusManager` | ✅ Production | Panel focus tracking with Tab cycling |
| `ControlBar` | ✅ Production | objectNames on Run/Stop/Loop/Watch buttons |
| CLI automation | ✅ Production | `--auto-run`, `--auto-quit`, `--probe`, `--watch`, `--overlay` |
| `ProbeState` enum | ✅ Production | ARMED, LIVE, STALE, INVALID |
| Unit tests | ⚠️ Partial | FocusManager, DockBar have unit tests; most GUI tests are E2E subprocess tests |
| `objectName` usage | ⚠️ Sparse | Only ControlBar buttons and ScalarWatchSidebar elements have objectNames |
| Signal exposure | ⚠️ Implicit | Signals exist but aren't catalogued or queryable |

### What's Missing

1. **Systematic `objectName` assignment** — MainWindow, CodeViewer, ProbeContainer, ProbePanels, Splitters all lack names.
2. **Widget registry / introspection API** — No way to query "give me all ProbePanels" or "what's the state of anchor X" without digging into private attrs.
3. **Structured action primitives** — Tests currently use raw QTest or subprocess CLI; no intermediate abstraction.
4. **Signal spy infrastructure** — No way to assert "signal X was emitted N times with args Y."
5. **Deterministic timing control** — No way to fast-forward timers or flush event queues precisely.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   LLM Test Architect                     │
│  (reads codebase, generates behavioral contracts,        │
│   generates structured test actions)                     │
└─────────────┬───────────────────────────┬───────────────┘
              │ contracts                  │ actions
              ▼                           ▼
┌─────────────────────┐   ┌──────────────────────────────┐
│  Contract Validator  │   │   AIGUITestHarness            │
│  (pytest assertions) │   │                              │
│                      │   │   .press_key("M")            │
│                      │◄──│   .click("runButton")        │
│                      │   │   .assert_prop("x", ...)     │
│                      │   │   .get_signal_count(...)      │
│                      │   │   .query_tree(...)            │
└──────────┬──────────┘   └──────────┬───────────────────┘
           │                         │
           ▼                         ▼
┌──────────────────────────────────────────────────────────┐
│               Introspection Layer                        │
│                                                          │
│   QObjectIntrospector    SignalSpy    WidgetRegistry     │
│   - tree traversal       - connect   - by objectName    │
│   - property query       - count     - by class         │
│   - class/name lookup    - args      - by anchor        │
│   - children listing     - wait      - by state         │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│               PyProbe Application (QApplication)          │
│                                                          │
│   MainWindow → ControlBar, CodeViewer, ProbeContainer    │
│   ProbeRegistry, FocusManager, StateTracer, DockBar      │
└──────────────────────────────────────────────────────────┘
```

---

## Milestones

### Milestone 0: Observability Foundation
**Objective:** Make the GUI codebase introspectable enough for automated testing.

**Deliverables:**
1. **Systematic `objectName` assignment** across all key widgets:
   - `MainWindow` → `"mainWindow"`
   - `CodeViewer` → `"codeViewer"`
   - `ProbePanelContainer` → `"probeContainer"`
   - Each `ProbePanel` → `"probe_{symbol}_{line}"` (dynamic)
   - `QSplitter` → `"mainSplitter"`
   - `DockBar` → `"dockBar"`
   - `ScalarWatchSidebar` → `"scalarWatchSidebar"`
   - `FocusManager` — already structural, no widget to name
2. **Widget catalog document** — machine-readable YAML/JSON listing all widgets, their objectNames, their class names, their parent, and their key properties/signals.
3. **`ProbePanel.objectName` auto-assignment** — set dynamically on creation based on anchor identity.

**Validation:**
- `QApplication.instance().findChild(QWidget, "codeViewer")` returns the CodeViewer.
- A script can walk the full QObject tree and produce a widget hierarchy dump.

**Risks:**
- None. This is pure additive work with zero behavioral impact.

**Effort:** 1–2 days.

---

### Milestone 1: Introspection Layer
**Objective:** Build a Python API that can query and traverse the live QObject tree.

**Deliverables:**
1. **`QObjectIntrospector` class** (`pyprobe/testing/introspect.py`):
   ```python
   class QObjectIntrospector:
       def __init__(self, root: QObject):
           ...
       def find_by_name(self, name: str) -> Optional[QObject]
       def find_by_class(self, cls: type) -> List[QObject]
       def find_by_name_pattern(self, pattern: str) -> List[QObject]
       def dump_tree(self, max_depth: int = 10) -> dict
       def get_properties(self, obj: QObject) -> dict
       def get_children(self, obj: QObject) -> List[QObject]
       def get_widget_geometry(self, widget: QWidget) -> dict
   ```
2. **`WidgetRegistry`** — thin wrapper that indexes the tree by objectName and class on construction, with a `refresh()` for after UI changes.
3. **`dump_widget_tree` CLI command** or pytest fixture that serializes the full tree to JSON.

**Validation:**
- `introspector.find_by_name("runButton")` returns the ControlBar's run button.
- `introspector.find_by_class(ProbePanel)` returns all active probe panels.
- `dump_tree()` output matches the expected widget structure for a known app state.

**Risks:**
- pyqtgraph widgets may not appear as standard QWidget children (they use their own scene graph). Need to verify `PlotWidget.getPlotItem()` children are walkable.
- Performance of deep tree walks on complex UIs — mitigate with caching and depth limits.

**Effort:** 2–3 days.

---

### Milestone 2: Signal Spy Infrastructure
**Objective:** Enable deterministic assertion on Qt signal emissions.

**Deliverables:**
1. **`SignalSpy` class** (`pyprobe/testing/signal_spy.py`):
   ```python
   class SignalSpy:
       def __init__(self, signal):
           """Connect to a signal and record all emissions."""
       @property
       def count(self) -> int
       @property  
       def calls(self) -> List[tuple]
       def wait(self, timeout_ms: int = 1000) -> bool
       def reset(self)
   ```
2. **`SignalRecorder`** — connects to multiple signals at once, useful for recording a full interaction sequence.
3. Integration with pytest: `spy = signal_spy(widget.some_signal)` as a fixture.

**Validation:**
- Spy on `ProbeRegistry.probe_added`, click a line in CodeViewer, assert spy.count == 1.
- Spy on `ControlBar.action_clicked`, simulate click on run button, assert emission.

**Risks:**
- Signal spy must handle cross-thread signals (MessageHandler uses QTimer-based polling). May need `QSignalSpy` from `PyQt6.QtTest` if available, or custom implementation.
- Disconnecting spies cleanly in teardown to avoid dangling connections.

**Effort:** 1–2 days.

---

### Milestone 3: AIGUITestHarness — Structured Action Primitives
**Objective:** Build the domain-specific testing API that replaces raw QTest calls.

**Deliverables:**
1. **`AIGUITestHarness` class** (`pyprobe/testing/harness.py`):
   ```python
   class AIGUITestHarness:
       def __init__(self, app: QApplication, window: MainWindow):
           ...
       
       # === Actions ===
       def press_key(self, key: str, modifiers: list[str] = None)
       def click_widget(self, object_name: str)
       def click_code_line(self, line: int, col: int = 0)
       def right_click_widget(self, object_name: str)
       def drag_drop(self, source_name: str, target_name: str)
       def type_text(self, text: str)
       
       # === State Queries ===
       def get_property(self, object_name: str, prop: str) -> Any
       def is_visible(self, object_name: str) -> bool
       def is_enabled(self, object_name: str) -> bool
       def get_probe_state(self, symbol: str) -> str
       def get_probe_count(self) -> int
       def get_focused_panel(self) -> Optional[str]
       def get_control_bar_state(self) -> dict  # {running, paused, loop}
       
       # === Signal Assertions ===
       def spy_signal(self, object_name: str, signal_name: str) -> SignalSpy
       def get_signal_count(self, object_name: str, signal_name: str) -> int
       
       # === Tree Queries ===
       def query_tree(self, filter: dict = None) -> list[dict]
       def find_widget(self, name: str) -> dict  # {class, visible, enabled, geometry, ...}
       
       # === Compound Actions ===
       def load_and_run(self, script_path: str)
       def add_probe(self, line: int, symbol: str, instance: int = 1)
       def wait_for_probe_state(self, symbol: str, state: str, timeout_ms: int = 5000)
       def wait_for_idle(self, timeout_ms: int = 5000)
       
       # === Event Loop Control ===
       def process_events(self, ms: int = 0)
       def flush_timers(self)
   ```

2. **Pytest fixtures:**
   ```python
   @pytest.fixture
   def harness(qtbot):
       app = QApplication.instance() or QApplication([])
       window = MainWindow()
       window.show()
       h = AIGUITestHarness(app, window)
       yield h
       window.close()
   ```

3. **Action logging** — every harness action appends to a structured log compatible with StateTracer format.

**Validation:**
- Write 3 real test cases using the harness:
  1. Load script → Run → Verify probe state transitions (ARMED→LIVE)
  2. Click line → Add probe → Verify panel created → Press key → Panel maximizes
  3. Toggle loop → Run → Verify loop restart
- Each test uses zero raw QTest calls.

**Risks:**
- Event loop processing: `process_events()` timing must be reliable. Tests that don't wait long enough will be flaky.
- Focus behavior: QTest key events go to the focused widget, which must be managed carefully.
- Compound actions (load_and_run) may hide timing issues.

**Effort:** 3–4 days.

---

### Milestone 4: Behavioral Contract System
**Objective:** Define a structured format for behavioral test specifications that an LLM can generate and reason about.

**Deliverables:**
1. **Contract schema** (YAML or Python dataclass):
   ```yaml
   contract:
     name: "Panel maximize on M key"
     preconditions:
       - probe_exists: {symbol: "signal_i"}
       - panel_focused: {symbol: "signal_i"}
     action:
       press_key: {key: "M"}
     postconditions:
       - panel_visible: {symbol: "signal_i", expected: true}
       - panel_maximized: {symbol: "signal_i", expected: true}
       - other_panels_hidden: {except: "signal_i"}
     invariants:
       - probe_state: {symbol: "signal_i", state: "LIVE"}
   ```

2. **Contract runner** that:
   - Sets up preconditions using the harness
   - Executes the action
   - Validates all postconditions
   - Checks invariants

3. **Contract library** — initial set of 10–15 contracts covering core UX flows:
   - Script lifecycle (load → run → stop → loop)
   - Probe lifecycle (arm → live → stale → remove)
   - Focus cycling (Tab through panels)
   - Panel park/restore via DockBar
   - Scalar watch add/remove
   - Code viewer probe highlights

**Validation:**
- All 10–15 contracts pass on the current codebase.
- LLM can read a contract and explain what it tests.
- LLM can generate a new contract given a feature description.

**Risks:**
- Contract schema must be expressive enough for real UX scenarios but constrained enough to be unambiguous.
- Precondition setup may require multi-step harness interactions that are themselves timing-sensitive.

**Effort:** 3–4 days.

---

### Milestone 5: REPL-Based Live Interaction
**Objective:** Enable an LLM to interact with a running PyProbe instance through a Python REPL.

**Deliverables:**
1. **`pyprobe.testing.repl` module** — an IPython-compatible REPL that:
   - Connects to a running QApplication (same process, separate thread, or via IPC)
   - Exposes the `AIGUITestHarness` as `h`
   - Exposes the `QObjectIntrospector` as `tree`
   - Auto-imports common types
   - Processes Qt events between commands

2. **REPL launch mode:**
   ```bash
   python -m pyprobe --repl examples/dsp_demo.py
   ```
   Starts the app, loads the script, drops into REPL.

3. **Structured output mode** for LLM interaction:
   - `h.query_tree()` returns JSON
   - `h.get_probe_state("signal_i")` returns a string
   - All queries return machine-parseable output

4. **Safety guardrails:**
   - Read-only introspection by default
   - Actions require explicit confirmation or `--allow-actions` flag
   - State snapshots before/after each action for rollback reasoning

**Validation:**
- Launch REPL → `h.query_tree()` → get full widget dump.
- REPL → `h.click_code_line(42, 5)` → probe appears → `h.get_probe_count()` returns 1.
- LLM transcript: LLM explores tree → identifies widget → generates action → observes result → generates assertion.

**Risks:**
- Thread safety: Qt's event loop and REPL input loop must not deadlock. Standard approach: REPL runs in a background thread, actions are `QMetaObject.invokeMethod`'d to the main thread.
- Latency: cross-thread invocation adds ~1ms overhead per call, acceptable for interactive use.
- Scope creep: REPL can become a full debugger. Keep it focused on testing primitives.

**Effort:** 3–5 days.

---

### Milestone 6: LLM-Generated Test Suites
**Objective:** Close the loop — LLM reads codebase + contracts, generates new test suites.

**Deliverables:**
1. **Codebase digest for LLM context:**
   - Widget catalog (from M0)
   - Signal/slot map (from M2 infrastructure)
   - Existing contract library (from M4)
   - StateTracer log examples
2. **Prompt templates** for test generation:
   - "Given this widget structure, generate behavioral contracts for [feature]"
   - "Given this StateTracer log, identify untested state transitions"
   - "Given this bug report, generate a regression contract"
3. **Validation harness** — run LLM-generated contracts through the contract runner, report pass/fail.
4. **Feedback loop** — failed contracts produce structured error reports the LLM can use to iterate.

**Validation:**
- LLM generates 5 new contracts for an existing feature (e.g., DockBar) that all pass.
- LLM generates a contract for a known bug, and it correctly fails on the buggy code.

**Risks:**
- LLM may generate contracts that are technically valid but test trivial/obvious behavior.
- Contract failures may be ambiguous (is the contract wrong or the code wrong?).
- Requires good prompt engineering and codebase context selection.

**Effort:** 2–3 days (iteration-heavy, depends on M0–M5 quality).

---

## Observability Requirements Summary

| Requirement | Where | Priority | Milestone |
|-------------|-------|----------|-----------|
| `objectName` on all key widgets | `main_window.py`, `probe_panel.py`, etc. | **Critical** | M0 |
| Dynamic `objectName` on ProbePanels | `probe_panel.py` constructor | **Critical** | M0 |
| Widget catalog (machine-readable) | New file: `pyprobe/testing/widget_catalog.yaml` | High | M0 |
| Signal registry (queryable) | New: `pyprobe/testing/signal_map.py` | High | M2 |
| StateTracer always-on in test mode | `state_tracer.py` | Medium | M3 |
| Structured log format for all actions | Harness action logger | Medium | M3 |
| Event queue flush utility | New: `pyprobe/testing/event_utils.py` | High | M3 |

---

## Evolution Path

```
Current State                    Target State
─────────────                    ────────────
Raw QTest in pytest      →      Never used directly
Subprocess CLI E2E       →      Kept for smoke tests only
Ad-hoc widget tests      →      Replaced by contracts
Manual testing           →      Covered by LLM-generated contracts
No introspection API     →      Full tree + signal + property queries
No AI involvement        →      LLM generates, validates, and iterates on tests
```

---

## Concise Milestone List

| # | Milestone | Objective | Effort |
|---|-----------|-----------|--------|
| M0 | Observability Foundation | objectNames + widget catalog | 1–2 days |
| M1 | Introspection Layer | QObject tree query API | 2–3 days |
| M2 | Signal Spy Infrastructure | Deterministic signal assertions | 1–2 days |
| M3 | AIGUITestHarness | Structured action/query primitives | 3–4 days |
| M4 | Behavioral Contracts | YAML-defined test specifications | 3–4 days |
| M5 | REPL Live Interaction | LLM-interactive REPL mode | 3–5 days |
| M6 | LLM-Generated Tests | Closed-loop AI test generation | 2–3 days |

**Total estimated effort:** 15–23 days (solo developer).

---

## Suggested Starting Milestone

**Start with M0 + M1 combined** (3–4 days).

Rationale:
- M0 is trivial but required by everything else.
- M1 immediately validates the core bet: "can we introspect PyProbe's widget tree well enough to drive tests?"
- If M1 reveals that pyqtgraph widgets are opaque or the tree is too dynamic, we learn that in days, not weeks.
- M1's `dump_tree()` output becomes the first artifact the LLM can reason about.

---

## First 2-Week Execution Strategy

### Week 1: Foundation + Proof of Viability

**Days 1–2: M0 — Observability**
- Add `objectName` to all major widgets (half-day task).
- Write `dump_widget_tree.py` script that launches app, walks tree, dumps JSON.
- Verify pyqtgraph `PlotWidget` children are visible in the tree.
- Create initial widget catalog YAML.

**Days 3–5: M1 + M2 — Introspection + Signals**
- Build `QObjectIntrospector` with `find_by_name`, `find_by_class`, `dump_tree`.
- Build `SignalSpy` wrapping `QSignalSpy` or custom implementation.
- Write 3 pytest tests proving:
  1. Tree contains expected widgets after app launch.
  2. Signal spy captures `probe_added` when clicking a code line.
  3. Property query returns correct `ControlBar` state.
- **Decision gate:** If pyqtgraph introspection is problematic, design a workaround (expose plot state via properties rather than tree walk).

### Week 2: Harness + First Contracts

**Days 6–8: M3 — AIGUITestHarness**
- Implement action primitives: `press_key`, `click_widget`, `click_code_line`.
- Implement state queries: `get_probe_state`, `get_probe_count`, `is_visible`.
- Implement compound actions: `load_and_run`, `add_probe`, `wait_for_idle`.
- Migrate 2 existing tests (e.g., `test_focus_manager`, `test_dock_bar`) to use the harness. Verify no regressions.

**Days 9–10: M4 (partial) — First Contracts**
- Define the YAML contract schema.
- Write the contract runner (precondition setup → action → postcondition check).
- Author 5 initial contracts covering:
  1. Script run lifecycle
  2. Probe add/remove
  3. Focus cycling
  4. Panel park/restore
  5. Probe state transitions
- Run all contracts in CI.

**End of Week 2 Deliverable:**
- Working `AIGUITestHarness` with ~15 primitives.
- 5 behavioral contracts passing in CI.
- Full widget tree introspection.
- Signal spy infrastructure.
- Clear evidence of viability (or clear identification of blocking issues).

After week 2, the system is ready for M5 (REPL) and M6 (LLM-generated tests), which are the "AI-native" phases. Weeks 1–2 build the substrate that makes those phases tractable.
