# PyProbe Backlog

> Priority-ordered bugs and features. Update via `@[prompts/END.md]` hook.

## P1 - High Priority

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
