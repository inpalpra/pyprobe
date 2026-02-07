# Button State Bug - Debugging Report

## Problem Statement

The PyProbe application's button states (Run/Pause/Stop/Loop) become inconsistent:
1. **Non-loop mode**: Action button gets stuck at "PAUSE" after script finishes
2. **Loop mode**: Script loops a few times, then GUI freezes while script continues looping

## Root Causes Identified

### Root Cause 1: Queue Feeder Race Condition (FIXED)
**Location**: `runner.py` → `run_script_subprocess()`

The subprocess sends `DATA_SCRIPT_END` via `queue.put()`, then immediately calls `os._exit()`. However, `put()` uses a background feeder thread, and `os._exit()` terminates the process before the feeder completes.

**Fix Applied**: Added 100ms sleep before `os._exit()` to allow feeder thread to complete.

```python
time.sleep(0.1)  # Give feeder thread time to send DATA_SCRIPT_END
os._exit(exit_code)
```

### Root Cause 2: IPC Cleanup Draining Queue (FIXED)
**Location**: `runner.py` → `run_script_subprocess()`

Originally called `ipc.cleanup()` which drains the data queue, removing `DATA_SCRIPT_END`.

**Fix Applied**: Removed `ipc.cleanup()` call, only cancel join threads.

## Fixes Applied

| File | Change | Status |
|------|--------|--------|
| `runner.py` | Added 100ms sleep before `os._exit()` | ✅ WORKING |
| `runner.py` | Removed queue draining in subprocess | ✅ Applied |
| `runner.py` | Added retry loop for DATA_SCRIPT_END send | ✅ Applied |
| `main_window.py` | Added subprocess exit fallback detection | ✅ Applied |
| `main_window.py` | Added tracer hooks for debugging | ✅ Applied |

## Test Results

### TEST 1 (No Loop) - ✅ FIXED
```
[  10.287s] IPC_RECV | DATA_SCRIPT_END (subprocess_alive=True)
[  10.287s] script_ended signal
[  10.287s] cleanup complete, now IDLE (button=Run)
```

### TEST 2 (Loop Mode) - ⚠️ NEEDS TESTING
Previous issues:
- After loop #1, subsequent iterations sometimes miss `DATA_SCRIPT_END`
- Probe data (`DATA_PROBE_VALUE_BATCH`) stops being sent after first loop

## Remaining Issues to Investigate

### 1. Loop Mode Probe Registration
After first loop ends, subsequent subprocess instances don't receive probe data:
- `CMD_ADD_PROBE` commands may be sent before subprocess is ready
- Need to verify command listener thread is started before sending commands

### 2. Loop Mode GUI Freeze
Even when terminal shows continuous looping, GUI shows frozen at "PAUSE":
- May be related to `_soft_cleanup_for_loop()` stopping poll timer
- Or race between cleanup and restart

### 3. Intermittent DATA_SCRIPT_END Loss in Loop Mode
Sometimes received, sometimes not. The 100ms sleep should help, but loop mode has additional complexity with queue reuse across subprocess restarts.

## State Tracer Usage

Enable detailed tracing with:
```bash
python -m pyprobe --trace-states examples/dsp_demo.py 2>&1 | tee /tmp/pyprobe_full.log
```

Log location: `/tmp/pyprobe_state_trace.log`

## Key Code Locations

- **Button state machine**: `main_window.py` → `_on_script_ended()`, `_cleanup_run()`
- **Loop restart**: `main_window.py` → `_soft_cleanup_for_loop()`, `_restart_loop()`
- **Subprocess cleanup**: `runner.py` → `run_script_subprocess()` finally block
- **IPC message handling**: `main_window.py` → `_poll_ipc()`, `_handle_message()`
- **State tracer**: `state_tracer.py`

## Next Steps

1. **Test Loop Mode** with current fixes
2. **Add synchronization** between subprocess start and probe command sending
3. **Consider using join_thread()** instead of sleep for more reliable queue flush
4. **Add tracer hooks** to `_restart_loop()` for looped DATA_PROBE_VALUE_BATCH tracking
