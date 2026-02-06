# PyProbe Backlog

> Priority-ordered bugs and features. Update via `@[prompts/END.md]` hook.

## P1 - High Priority

### BUG: Waveform collection t0 not honored in plot
- **Symptom**: Waveforms in a collection all start at x=0 instead of their specified t0
- **Expected**: Waveform with t0=10 should start at x=10 on the plot  
- **Impact**: Cannot visualize time-offset waveforms correctly
- **Repro**: `examples/waveform_collection_demo.py` with waveforms at t0=0, 10, 15
- **Root cause**: Likely in `_update_waveform_collection_data()` or scalar sorting logic in `waveform_plot.py`

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
