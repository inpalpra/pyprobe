# Bug Progress Report: Overlay Race Condition & Data Drop

## Problem Statement
CI tests (specifically `TestE2ECapturePipelineFast`) were intermittently failing with `AssertionError` because overlay data for the second frame (Frame 1) was missing from the `PLOT_DATA` export during `--auto-quit` runs.

## Root Cause Analysis
Several layered issues contributed to this failure:

1.  **Deferred Captures Not Flushed:** `VariableTracer` used deferred captures for LHS assignments. If the script ended immediately after an assignment, the data remained in `CaptureManager` without being sent.
2.  **Premature IPC Cleanup:** In `main_window.py`, the `_on_script_ended` handler was calling `self._script_runner.cleanup()` before `_export_plot_data()`, which destroyed shared memory resources needed by the GUI to read array data.
3.  **Aggressive IPC Draining:** `MessageHandler._drain_after_end` used a 0ms timeout, potentially missing final `PLOT_DATA` messages if they arrived slightly after the `DATA_SCRIPT_END` packet.
4.  **Downsampling Shape Mismatch (GUI):** A critical bug was found in `ProbeController._add_overlay_to_waveform`. When complex data exceeded `MAX_DISPLAY_POINTS`, it called `real_data = plot.downsample(real_data)`. Since `downsample` returns a tuple `(x, y)`, `real_data` became a tuple, causing `curve.setData(x, real_data)` to fail silently in PyQtGraph.

## Changes Made

### Core / Tracer
- **`pyprobe/core/capture_manager.py`**: Added `flush_all()` to force-flush all pending deferred captures.
- **`pyprobe/core/tracer.py`**: Modified `VariableTracer.stop()` to call `capture_manager.flush_all()`.

### GUI / IPC
- **`pyprobe/gui/main_window.py`**:
    - Modified `_on_script_ended` to defer `self._script_runner.cleanup()` until *after* `_export_plot_data()` completes in the `--auto-quit` path.
    - Ensured `_export_plot_data` calls `processEvents()` and waits for zoom/redraw timers.
- **`pyprobe/gui/message_handler.py`**: Modified `_drain_after_end` to use a 10ms timeout (`timeout=0.01`) to catch late packets.
- **`pyprobe/gui/probe_controller.py`**: Fixed the `_add_overlay_to_waveform` decimation bug by properly unpacking the `(x, y)` tuple from `plot.downsample()`.

## Current Status
- The "Shape Mismatch" bug is fixed.
- Premature cleanup is fixed.
- Local verification using `slow_test.py` (a wrapper around `dsp_demo_two_frames.py`) shows that `DATA_PROBE_VALUE_BATCH` now consistently reaches the GUI for all frames.

## Next Steps for AI Agent
1.  **Verify CI:** Run the `test-only.yml` workflow on GitHub to see if the random failures in `test_e2e_capture_pipeline_fast.py` are resolved.
2.  **Check Throttling:** If data still drops, investigate `VariableTracer`'s 50ms throttle. High-frequency loops (e.g. 10ms sleeps) might still be throttled by the tracer itself. Consider disabling throttling when `--auto-run` or `--auto-quit` is active.
3.  **Legend Cleanup:** Verify that closing a panel properly cleans up legend items and overlay highlights (code viewer/gutter) to avoid ghost probes in long CI runs.

## Technical Notes
- **IPC:** Debugging IPC requires checking `stderr` for `PLOT_DATA:` lines. Use `PYPROBE_LOG_LEVEL=DEBUG` but note that the tracer subprocess handles logs separately.
- **Qt Events:** `QApplication.processEvents()` is critical before scraping widget data, as many UI updates are queued via `QTimer.singleShot`.
