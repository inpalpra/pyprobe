# PyProbe Backlog

> Priority-ordered bugs and features. Update via `@[prompts/END.md]` hook.

## P1 - High Priority

### [M2.5] Drag-and-drop symbols to graph not working
- Mouse-down immediately creates/removes a probe (no time to drag)
- **Root cause**: Using mouse-down event instead of mouse-up
- **Expected behavior**:
  - Mouse-down on symbol: start drag operation
  - Mouse-up on code area: toggle probe (existing behavior)
  - Mouse-up on graph area: add symbol to that graph
- **File**: `code_panel.py`, `graph_area.py`

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
