# PyProbe Backlog

> Priority-ordered bugs and features. Update via `@[prompts/END.md]` hook.

## P1 - High Priority

### BUG: Probe updates not in sync for related variables
- **Symptom**: Probing both `wfm` and `x` on same line shows different graphs at same instant
- **Expected**: Probes for related/equivalent data should update atomically
- **Impact**: Breaks user trust in probe accuracy
- **Repro**: `examples/waveform_demo.py` line 56, probe `wfm` and `x`, observe async updates at 10fps
- **Root cause**: IPC queue delivers messages independently, no batching per trace event

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
