# CI Debug Report: Overlay Test Failure

## Overview
Status: **Investigating**
Root Cause Category: **Race condition between GUI update and Auto-Quit export**
Primary Symptom: `test_overlay_drag_drop_two_frames_fast.py` reports Frame 0 data instead of Frame 1 data on CI, while passing locally.

## Evidence & Experiments

### Experiment 1: Added internal diagnostics (`[DIAG-BUF]` and `[DIAG-PANEL]`)
**What we did**: Added prints in `export_and_quit` to dump the state of the `RedrawThrottler` buffers and the actual `ProbePanel` curve data right before export.
**Result**: 
- `[DIAG-BUF]` (Throttler Memory): **PASS** (Correct Frame 1 data found).
- `[DIAG-PANEL]` (Widget Data): **FAIL** (Stale Frame 0 data found).

### Experiment 2: Added `_force_redraw()` to `_force_quit()` path
**What we did**: Suspected that CI might be exiting via the 15s timeout path, which didn't have a buffer flush.
**Result**: Exit path was confirmed to be `export_and_quit` (script-ended), not timeout. However, `_force_redraw` in `export_and_quit` still failed to update the widget.

### Experiment 3: Added `-s` to pytest
**What we did**: Enabled uncaptured output to see the diagnostic prints from `setUpClass` and the subprocess.
**Result**: Confirmed the discrepancy between memory (correct) and widget (stale).

## Conclusions So Far
- **IPC works**: Frame 1 data successfully reaches the GUI process and survives in the throttler's memory buffer.
- **Throttling is NOT the cause**: `_force_redraw()` explicitly pulls from the buffer, but the `WaveformWidget` data export still retrieves old data.
- **The Gap**: Even after calling `update_data` on the widget, the internal state (especially for curves and overlays) might be asychronously updated via Qt's event loop. 

## Next Steps
1. **Targeted Workflow**: Use `debug-targeted.yml` (as requested) to isolate these 2 tests and iterate faster without the noise of the full suite.
2. **Synchronous Flourish**: Modify `WaveformWidget` (and others) to allow a synchronous "flush" or force-draw that immediately updates its internal curve data without waiting for the next paint event.
3. **Event Loop Draining**: Increase the `QApplication.processEvents()` depth during export.

## Metadata of Failure
- **Commit**: `34ed4c5`
- **Run ID**: `22533427606`
- **Error**: `AssertionError: -0.179 != 0.466` (Frame 0 value where Frame 1 expected).
