# Debug: Drag-and-Drop Symbol Overlay Not Working

## Problem
Dragging a symbol from the code viewer onto an existing waveform graph should overlay the dragged signal on the target graph. Currently, the overlay is not appearing.

## What Was Implemented

### 1. Code Viewer (`pyprobe/gui/code_viewer.py`)
- **Fixed**: Probe toggle moved from `mousePressEvent` to `mouseReleaseEvent`
- **Fixed**: Text selection prevented by `event.accept()` and not calling `super()`
- **Fixed**: Drag initiates after 10px manhattan distance
- Drag creates QMimeData with anchor info via `encode_anchor_mime()`

### 2. Probe Panel (`pyprobe/gui/probe_panel.py`)
- `setAcceptDrops(True)` is set in `__init__` (line 70)
- `dragEnterEvent`: accepts anchor MIME, shows green highlight
- `dropEvent`: decodes anchor, emits `overlay_requested(self, anchor)` signal
- Signal changed from `pyqtSignal(object)` to `pyqtSignal(object, object)` for (panel, anchor)

### 3. Main Window (`pyprobe/gui/main_window.py`)
- `_on_overlay_requested(target_panel, overlay_anchor)`: Registers overlay anchor on target panel
- `_forward_overlay_data(anchor, payload)`: Routes overlay data to target panels
- `_add_overlay_to_waveform(plot, symbol, value, dtype, shape)`: Creates curve on plot

## Likely Issues to Investigate

1. **Drop not being received**: Add print statements to `ProbePanel.dragEnterEvent` and `ProbePanel.dropEvent` to verify drops are being detected.

2. **Signal connection**: Check if `overlay_requested.connect(self._on_overlay_requested)` in `main_window.py` line 496 is being called with correct signature (now expects 2 args).

3. **Data forwarding**: The overlay data arrives via `DATA_PROBE_VALUE` messages. Add prints in `_forward_overlay_data` to verify data is being routed.

4. **Curve creation**: Add prints in `_add_overlay_to_waveform` to verify curves are being created.

## Quick Test Steps

1. Run demo: `python -m pyprobe examples/dsp_demo.py`
2. Click on `signal_i` to probe it (waveform graph appears)
3. Drag `signal_q` onto the `signal_i` graph
4. Check console for any print/debug output

## Files to Focus On

- `/Users/ppal/repos/pyprobe/pyprobe/gui/code_viewer.py` (drag source)
- `/Users/ppal/repos/pyprobe/pyprobe/gui/probe_panel.py` (drop target)
- `/Users/ppal/repos/pyprobe/pyprobe/gui/main_window.py` (overlay handler)
- `/Users/ppal/repos/pyprobe/pyprobe/gui/drag_helpers.py` (MIME encoding)

## Recommended Debug Approach

Add print statements to trace the full flow:
```python
# In ProbePanel.dragEnterEvent
print(f"[DROP] dragEnterEvent: has_anchor={has_anchor_mime(event.mimeData())}")

# In ProbePanel.dropEvent  
print(f"[DROP] dropEvent: anchor={anchor.symbol if anchor else None}")

# In MainWindow._on_overlay_requested
print(f"[OVERLAY] _on_overlay_requested: target={target_panel._anchor.symbol}, overlay={overlay_anchor.symbol}")

# In MainWindow._forward_overlay_data
print(f"[OVERLAY] _forward_overlay_data: anchor={anchor.symbol}")
```
