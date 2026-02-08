# Sub-Agent 6: Signal Overlay (Drag-Drop)

## Overview

Implement signal overlay — dragging a symbol from code view onto an existing graph.

## Goal

Enable drag-and-drop from CodeViewer to ProbePanel for overlaying signals.

## Reference Files

- [code_viewer.py](file:///Users/ppal/repos/pyprobe/pyprobe/gui/code_viewer.py)
- [probe_panel.py](file:///Users/ppal/repos/pyprobe/pyprobe/gui/probe_panel.py)
- [waveform_plot.py](file:///Users/ppal/repos/pyprobe/pyprobe/plots/waveform_plot.py)
- [R5 requirements](file:///Users/ppal/repos/pyprobe/plans/implementation/m2.5/graph-palette/graph-palette-requirements.md)

## Constraints

- All overlaid signals share same axes
- Each signal has own color + legend entry
- Signals can be removed independently
- Valid drop targets highlight on drag

---

## MIME Type

Format: `application/x-pyprobe-anchor`

```json
{"file": "/path/to/file.py", "line": 42, "col": 8, "symbol": "signal_x", "func": "process"}
```

---

## Deliverables

### 1. Modify: `code_viewer.py`

```python
def mouseMoveEvent(self, event):
    if self._drag_start_pos and (event.pos() - self._drag_start_pos).manhattanLength() > 10:
        self._start_drag()

def _start_drag(self):
    drag = QDrag(self)
    mime_data = QMimeData()
    mime_data.setData('application/x-pyprobe-anchor', anchor_json.encode())
    drag.setMimeData(mime_data)
    drag.exec(Qt.DropAction.CopyAction)
```

### 2. Modify: `probe_panel.py`

```python
self.setAcceptDrops(True)

def dragEnterEvent(self, event):
    if event.mimeData().hasFormat('application/x-pyprobe-anchor'):
        event.accept()
        self._show_drop_highlight(True)

def dropEvent(self, event):
    self._show_drop_highlight(False)
    anchor = parse_anchor(event.mimeData())
    self.overlay_requested.emit(anchor)
```

### 3. Modify: `waveform_plot.py`

```python
def add_overlay(self, anchor, color):
    curve = self._plot_item.plot(pen=color)
    self._overlay_curves[anchor] = curve
    self._update_legend()

def remove_overlay(self, anchor):
    self._plot_item.removeItem(self._overlay_curves.pop(anchor))
```

---

## Unit Tests

Create `tests/test_signal_overlay.py`:

```python
def test_add_overlay_creates_curve(waveform_plot, anchor):
    waveform_plot.add_overlay(anchor, QColor("magenta"))
    assert len(waveform_plot._overlay_curves) == 1

def test_remove_overlay(waveform_plot, anchor):
    waveform_plot.add_overlay(anchor, QColor("magenta"))
    waveform_plot.remove_overlay(anchor)
    assert len(waveform_plot._overlay_curves) == 0
```

---

## Success Criteria

- [ ] Drag from code view initiates with anchor data
- [ ] Valid drop targets highlight
- [ ] Drop adds overlay curve
- [ ] Legend shows all signals
- [ ] Overlay signals removable independently
