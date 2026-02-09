# PyProbe Backlog

> Priority-ordered bugs and features. Update via `@[prompts/END.md]` hook.

## P1 - High Priority

### BUG: No way to remove a variable from an overlaid graph
- Once a variable is dragged and dropped into an existing graph, there is no way to remove it from that graph.
- Clicking the overlaid variable does not remove it.
- Clicking it also does not create a new dedicated graph window for it.

### BUG: Cannot overlay onto graph if both variables already have dedicated graphs
- If two signals (e.g., `signal_i` and `signal_q`) are probed in separate graphs, dragging `signal_i` from code area to `signal_q`'s graph does not overlay them.
- However, if `signal_i` is probed first, then `signal_q` is drag-dropped onto `signal_i`'s graph (without creating a dedicated graph for `signal_q` first), overlay works correctly.

### BUG: Missing plot legends after drag-drop overlay
- After drag-dropping a variable onto an existing graph, no plot legend is created for the newly added traces.
- Example: dragging `received_symbols` to `signal_i`'s graph shows real/imag parts plotted, but without corresponding legend entries.

---

## P1.5 - Refactoring (AI Agent Efficiency)

### REFACTOR: Extract components from `main_window.py` (1061 lines)
- **Problem**: God class with 34 methods handling script execution, IPC, probes, panels
- **Extract**: `ScriptRunner`, `MessageHandler`, `ProbeController`
- **Effort**: 2-3 days
- **Impact**: Critical - every bug fix touches this file

### REFACTOR: Split `probe_panel.py` (811 lines)
- **Problem**: Two unrelated classes bundled (`ProbePanel` + `ProbePanelContainer`)
- **Extract**: Move `ProbePanelContainer` to `panel_container.py`
- **Effort**: 2 hours

### REFACTOR: Consolidate `waveform_plot.py` + plugin `waveform.py`
- **Problem**: 90% code duplication between legacy plot and plugin widget
- **Action**: Migrate `plot_factory.py` to use plugin system, then delete legacy
- **Effort**: 4 hours

### REFACTOR: Simplify `tracer.py` (630 lines)
- **Problem**: Dual trace paths (`_trace_func` and `_trace_func_anchored`)
- **Action**: Deprecate legacy `_trace_func`, extract `DeferredCaptureManager`
- **Effort**: 1 day

---

## P2 - Medium Priority

### Custom probes per symbol type
- **Function calls**: Display return value
- **Module refs**: Display module name/path
- **Class refs**: Display class info

### Symbol type indicator in probe panel
- Show icon/badge indicating if symbol is DATA_VARIABLE, FUNCTION_CALL, etc.
- Help user understand why "Nothing to show" appears

---

## P3 - Future

### Expression probing
- Probe arbitrary expressions like `np.sin(x)` for return value
- Requires tracer enhancements

### Probe persistence
- Save/restore probe configurations across sessions
- Remember which variables user typically watches
