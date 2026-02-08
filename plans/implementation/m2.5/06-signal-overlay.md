# Sub-Agent 06: Signal Overlay (Drag-Drop)

## Context

You are implementing signal overlay — dragging a symbol from the code view onto an existing graph to overlay its data.

## Goal

Enable drag-and-drop from CodeViewer to ProbePanel for adding signals to an existing plot.

## Constraints

- All overlaid signals share same axes
- Axis operations affect all signals in graph
- Each signal retains own color + legend entry
- Signals can be removed independently
- Removing last signal clears graph
- Valid drop targets highlight on drag
- Invalid drops show rejection feedback
- No limit on overlaid signals per graph

## Expected Outputs

### Modifications to `CodeViewer`

Enable drag initiation:

```python
def mouseMoveEvent(self, event):
    if self._drag_start_pos is not None:
        if (event.pos() - self._drag_start_pos).manhattanLength() > 10:
            self._start_drag()

def _start_drag(self):
    drag = QDrag(self)
    mime_data = QMimeData()
    
    # Serialize anchor as JSON
    anchor_data = json.dumps({
        'file': self._hover_anchor.file,
        'line': self._hover_anchor.line,
        'col': self._hover_anchor.col,
        'symbol': self._hover_anchor.symbol,
        'func': self._hover_anchor.func,
    })
    mime_data.setData('application/x-pyprobe-anchor', anchor_data.encode())
    
    drag.setMimeData(mime_data)
    drag.exec(Qt.DropAction.CopyAction)
```

### Modifications to `ProbePanel`

Enable drop handling:

```python
def __init__(self, ...):
    ...
    self.setAcceptDrops(True)

def dragEnterEvent(self, event):
    if event.mimeData().hasFormat('application/x-pyprobe-anchor'):
        event.acceptProposedAction()
        self._show_drop_highlight(True)

def dragLeaveEvent(self, event):
    self._show_drop_highlight(False)

def dropEvent(self, event):
    self._show_drop_highlight(False)
    anchor_data = json.loads(
        event.mimeData().data('application/x-pyprobe-anchor').data().decode()
    )
    anchor = ProbeAnchor(**anchor_data)
    self.overlay_requested.emit(anchor)
```

### Modifications to `WaveformPlot`

Add overlay support:

```python
def add_overlay(self, anchor: ProbeAnchor, color: QColor) -> None:
    """Add an overlaid signal to this plot."""
    # Create new curve with unique color
    curve = self._plot_item.plot(pen=color)
    self._overlay_curves[anchor] = curve
    self._update_legend()

def remove_overlay(self, anchor: ProbeAnchor) -> None:
    """Remove an overlaid signal."""
    curve = self._overlay_curves.pop(anchor, None)
    if curve:
        self._plot_item.removeItem(curve)
        self._update_legend()
```

## Visual Feedback

| State | Visual |
|-------|--------|
| Valid drop target | Green border glow |
| Invalid drop (e.g., incompatible data) | Red flash, shake animation |
| Successful drop | New trace appears with legend entry |

## Integration Points

1. `CodeViewer` — initiate drag on mouse move (after press)
2. `ProbePanel` — accept drops, emit `overlay_requested`
3. `MainWindow` — handle `overlay_requested`, route data to overlay
4. `WaveformPlot` — add/remove overlay curves

## Test Plan

1. Unit test: `test_signal_overlay.py`
   - Create WaveformPlot with one curve
   - Call `add_overlay(anchor, color)`
   - Verify two curves exist
   - Call `remove_overlay(anchor)`
   - Verify one curve remains

2. Manual test:
   - Probe variable `x`
   - Click and drag variable `y` from code view
   - Drop on `x`'s panel
   - Verify both signals visible on same axes
   - Right-click → remove overlay
   - Verify only `x` remains

## Success Criteria

- [ ] Drag from code view initiates with anchor data
- [ ] Valid drop targets highlight green
- [ ] Drop adds overlay curve with new color
- [ ] Legend shows all signals
- [ ] Overlay signals can be removed independently
- [ ] Removing last signal clears graph
