# M2.5 Interface Contracts

This document defines the stable interfaces between Graph Palette components.

---

## AxisController Interface

```python
class AxisController:
    """Manages axis pin state for a PlotItem."""
    
    # Properties
    x_pinned: bool       # Read-only
    y_pinned: bool       # Read-only
    
    # Methods
    def is_pinned(self, axis: str) -> bool
    def set_pinned(self, axis: str, pinned: bool) -> None
    def toggle_pin(self, axis: str) -> None
    def reset(self) -> None
    
    # Signals emitted from controller
    pin_state_changed = Signal(str, bool)  # axis, is_pinned
```

**Contract:**
- `set_pinned('x', True)` → disables X autoscale on PlotItem
- `reset()` → unpins both axes AND triggers immediate autoscale
- Pin state is persistent until explicitly changed

---

## PlotToolbar Interface

```python
class InteractionMode(Enum):
    POINTER = auto()
    PAN = auto()
    ZOOM = auto()
    ZOOM_X = auto()
    ZOOM_Y = auto()

class PlotToolbar:
    # Properties
    current_mode: InteractionMode
    
    # Methods
    def set_mode(self, mode: InteractionMode) -> None
    def show_on_hover(self) -> None
    def hide_on_leave(self) -> None
    
    # Signals
    mode_changed = Signal(InteractionMode)
    reset_requested = Signal()
```

**Contract:**
- Default mode is always POINTER
- After pan/zoom action completes, mode auto-reverts to POINTER
- `reset_requested` signal triggers `AxisController.reset()`

---

## LayoutManager Interface

```python
class LayoutManager:
    # Properties
    maximized_panel: Optional[QWidget]
    
    # Methods
    def toggle_maximize(self, panel: QWidget) -> None
    def restore(self) -> None
    def is_maximized(self) -> bool
    
    # Signals
    layout_changed = Signal()  # Emitted after any state change
```

**Contract:**
- Only one panel can be maximized at a time
- `toggle_maximize(P)` when P is maximized → restores to grid
- Hidden panels remain alive and receive data updates

---

## DockBar Interface

```python
class DockBar:
    # Methods
    def add_panel(self, anchor_key: str, title: str, color) -> None
    def remove_panel(self, anchor_key: str) -> None
    def update_data(self, anchor_key: str, data) -> None
    def is_empty(self) -> bool
    
    # Signals
    panel_restore_requested = Signal(str)  # anchor_key
```

**Contract:**
- `add_panel` makes bar visible if currently hidden
- `remove_panel` may hide bar if now empty
- `update_data` updates sparkline for parked panel

---

## FocusManager Interface

```python
class FocusManager:
    # Properties
    focused_panel: Optional[QWidget]
    
    # Methods
    def set_focus(self, panel: QWidget) -> None
    def clear_focus(self) -> None
    def focus_next(self) -> None
    
    # Signals
    focus_changed = Signal(object)  # panel or None
```

**Contract:**
- Only one panel can have focus at a time
- `set_focus(P)` clears previous focus first
- `focus_next()` cycles in grid order, wraps around

---

## Signal Overlay Interface

### ProbePanel (Drop Target)

```python
class ProbePanel:
    # Signals
    overlay_requested = Signal(object)  # ProbeAnchor
    
    # Methods for WaveformPlot
    def add_overlay(self, anchor: ProbeAnchor, color: QColor) -> None
    def remove_overlay(self, anchor: ProbeAnchor) -> None
```

### WaveformPlot

```python
class WaveformPlot:
    # Methods
    def add_overlay(self, anchor: ProbeAnchor, color: QColor) -> None
    def remove_overlay(self, anchor: ProbeAnchor) -> None
    def get_overlay_anchors(self) -> List[ProbeAnchor]
```

**Contract:**
- Overlaid signals share axes with primary signal
- Axis operations affect all overlaid signals
- Removing last signal clears the graph

---

## MIME Type for Drag-Drop

Format: `application/x-pyprobe-anchor`

Content: JSON-encoded ProbeAnchor

```json
{
    "file": "/path/to/file.py",
    "line": 42,
    "col": 8,
    "symbol": "signal_x",
    "func": "process",
    "is_assignment": false
}
```
