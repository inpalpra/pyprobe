# PyProbe Backlog

> Priority-ordered bugs and features. Update via `@[prompts/END.md]` hook.

## P1 - High Priority

### BUG: Parked graph doesn't release space to remaining graphs
- When multiple variables are probed (e.g., `signal_i` and `signal_q`) and one is parked, the remaining graph doesn't expand to occupy the full graphing area automatically.
- **Ref**: `examples/dsp_demo.py` line 72

### BUG: Multiple graphs don't auto-arrange when one is parked
- Similar to above: if there are multiple graph panels and one is parked, the remaining graphs should auto-resize to fill the available graphing area.

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
