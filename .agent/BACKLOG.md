# PyProbe Backlog

> Priority-ordered bugs and features. Update via `@[prompts/SESSION-END.md]` hook.

## P1 - High Priority

### Scalar value history graphs
- Plot scalar values over time across multiple runs
- Show trend and historical values
- Useful for convergence debugging

### B1 constellation-graph-no-data (INTERMITTENT)
**Status:** Hard to reproduce

**Symptoms:**
- Click wrong symbol first (e.g., `np`)
- Click target symbol (`received_symbols`)
- Press RUN
- Panel exists but constellation graph shows nothing

**Works when:**
- Fresh open → click `received_symbols` directly → RUN → graph appears

**Suspected area:**
- Data flow timing between panel creation and runner IPC
- Registry `active_anchors` sync with `_probe_panels`
- Possible race with animation callbacks

**Next steps when reproducible:**
1. Capture full debug log with probe_panel.py logging
2. Check if panel is in `active_anchors` when runner starts
3. Verify IPC messages include correct anchor

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
