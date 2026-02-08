# Sub-Agent 04: Maximize/Restore

## Context

You are implementing double-click to maximize and double-click again to restore for PyProbe graphs.

## Goal

Allow users to double-click a plot background to expand it to fill the container, hiding other plots but keeping them alive and updating.

## Constraints

- Double-click on background only (not on axes, tick labels, or traces)
- Animation required: 150-200ms transition
- Other plots remain alive and updating
- No modifier keys required

## Hit-Test Priority (Critical)

Maximize must NOT trigger if double-click lands on:

| Priority | Target | Action |
|----------|--------|--------|
| 1 (Highest) | Axis tick label | In-place edit mode |
| 2 | Axis line/region | Ignored |
| 3 | Data traces | Ignored |
| 4 (Lowest) | Empty plot background | Toggle maximize |

## Expected Outputs

### File: `pyprobe/gui/layout_manager.py`

```python
from typing import Optional
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

class LayoutManager:
    """Manages maximize/restore state for probe panels.
    
    Only one panel can be maximized at a time.
    Other panels remain hidden but continue updating.
    """
    
    def __init__(self, container: QWidget):
        self._container = container
        self._maximized_panel: Optional[QWidget] = None
    
    def toggle_maximize(self, panel: QWidget) -> None:
        """Toggle maximize state for a panel.
        
        If panel is currently maximized → restore
        If another panel is maximized → restore that, maximize this
        If no panel maximized → maximize this
        """
        ...
    
    def restore(self) -> None:
        """Restore grid layout."""
        ...
    
    def is_maximized(self) -> bool:
        """Check if any panel is maximized."""
        ...
    
    @property
    def maximized_panel(self) -> Optional[QWidget]:
        ...
```

### Modifications to `ProbePanel`

Override `mouseDoubleClickEvent`:

```python
def mouseDoubleClickEvent(self, event):
    # Hit-test priority check
    if self._is_on_axis_label(event.pos()):
        return  # Let axis editor handle it
    if self._is_on_axis(event.pos()):
        return  # Ignore
    if self._is_on_trace(event.pos()):
        return  # Ignore (future: trace selection)
    
    # Only background clicks reach here
    self.maximize_requested.emit()
```

### Modifications to `ProbePanelContainer`

```python
def __init__(self, ...):
    ...
    self._layout_manager = LayoutManager(self)

def _on_panel_maximize_requested(self, panel: ProbePanel):
    self._layout_manager.toggle_maximize(panel)
```

## Animation

```python
def _animate_maximize(self, panel: QWidget):
    # Store original geometry
    self._original_geometries[panel] = panel.geometry()
    
    # Animate to full size
    anim = QPropertyAnimation(panel, b"geometry")
    anim.setDuration(175)
    anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
    anim.setStartValue(panel.geometry())
    anim.setEndValue(self._container.rect())
    anim.start()
    
    # Hide other panels
    for p in self._panels:
        if p != panel:
            p.hide()
```

## Integration Points

1. `ProbePanelContainer.__init__()` — instantiate LayoutManager
2. `ProbePanel` — add `maximize_requested` signal
3. Connect signal to `ProbePanelContainer._on_panel_maximize_requested()`

## Test Plan

1. Unit test: `test_layout_manager.py`
   - Verify initial state: no panel maximized
   - Call `toggle_maximize(panel1)` → panel1 maximized
   - Call `toggle_maximize(panel1)` again → restored
   - Call `toggle_maximize(panel2)` while panel1 maximized → panel1 restored, panel2 maximized

2. Manual test:
   - Probe two variables
   - Double-click on plot background of first panel
   - Verify first panel fills container, second hidden
   - Verify second panel still updates (check later)
   - Double-click background again
   - Verify grid layout restored

## Success Criteria

- [ ] Double-click background → maximize
- [ ] Double-click again → restore
- [ ] Clicking on axis/traces does NOT maximize
- [ ] Animation smooth (150-200ms)
- [ ] Hidden panels continue updating
- [ ] Axis states persist across maximize/restore
