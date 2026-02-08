# Sub-Agent 07: Keyboard Shortcuts and Focus Model

## Context

You are implementing keyboard shortcuts and focus model for graph interactions.

## Goal

Enable keyboard-driven control of focused plots with clear visual feedback.

## Focus Model

- Click anywhere on plot to give it keyboard focus
- Only one plot can have focus at a time
- Hover does NOT transfer focus (too erratic)
- Focused plot shows subtle visual indicator (border glow)
- Tab cycles through plots in grid order

## Keyboard Shortcuts

| Key | Action | Scope |
|-----|--------|-------|
| `X` | Toggle X-axis pin | Focused plot |
| `Y` | Toggle Y-axis pin | Focused plot |
| `R` | Reset view (unpin + autoscale) | Focused plot |
| `Escape` | Return to Pointer mode | Any plot |
| `Tab` | Cycle focus to next plot | Global |

## Expected Outputs

### File: `pyprobe/gui/focus_manager.py`

```python
from typing import Optional, List
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QObject, pyqtSignal

class FocusManager(QObject):
    """Manages keyboard focus for probe panels.
    
    Only one panel can have focus at a time.
    Provides visual feedback on focused panel.
    """
    
    focus_changed = pyqtSignal(object)  # ProbePanel or None
    
    def __init__(self, container: QWidget):
        ...
    
    def set_focus(self, panel: QWidget) -> None:
        """Set keyboard focus to panel."""
        ...
    
    def clear_focus(self) -> None:
        """Clear focus from all panels."""
        ...
    
    def focus_next(self) -> None:
        """Tab to next panel in grid order."""
        ...
    
    @property
    def focused_panel(self) -> Optional[QWidget]:
        ...
```

### Modifications to `ProbePanel`

```python
def __init__(self, ...):
    ...
    self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

def focusInEvent(self, event):
    self._show_focus_indicator(True)
    super().focusInEvent(event)

def focusOutEvent(self, event):
    self._show_focus_indicator(False)
    super().focusOutEvent(event)

def keyPressEvent(self, event):
    if event.key() == Qt.Key.Key_X:
        self._axis_controller.toggle_pin('x')
    elif event.key() == Qt.Key.Key_Y:
        self._axis_controller.toggle_pin('y')
    elif event.key() == Qt.Key.Key_R:
        self._axis_controller.reset()
    elif event.key() == Qt.Key.Key_Escape:
        self._toolbar.set_mode(InteractionMode.POINTER)
    else:
        super().keyPressEvent(event)

def _show_focus_indicator(self, focused: bool):
    """Show/hide subtle border glow."""
    if focused:
        self.setStyleSheet(self.styleSheet() + """
            ProbePanel {
                border: 1px solid #00ffff;
                box-shadow: 0 0 10px #00ffff;
            }
        """)
    else:
        # Reset to normal style
        ...
```

### Modifications to `ProbePanelContainer`

Handle Tab navigation:

```python
def keyPressEvent(self, event):
    if event.key() == Qt.Key.Key_Tab:
        self._focus_manager.focus_next()
        event.accept()
    else:
        super().keyPressEvent(event)
```

## Visual Feedback

| State | Visual |
|-------|--------|
| Focused | Subtle cyan border glow (#00ffff) |
| Unfocused | Normal dark border |

## Integration Points

1. `ProbePanelContainer` — instantiate FocusManager
2. `ProbePanel` — set focus policy, handle key events
3. Connect focus_changed → visual feedback

## Test Plan

1. Unit test: `test_focus_manager.py`
   - Create FocusManager with container
   - Call `set_focus(panel1)` → verify focused_panel == panel1
   - Call `focus_next()` → verify focused_panel == panel2

2. Manual test:
   - Probe two variables
   - Click on first plot → verify glow appears
   - Press `X` → verify X-axis pins
   - Press `Tab` → verify focus moves to second plot
   - Press `R` → verify second plot resets
   - Press `Escape` → verify mode returns to Pointer

## Success Criteria

- [ ] Click on plot gives it keyboard focus
- [ ] Focused plot shows cyan glow
- [ ] X/Y/R/Escape keys work on focused plot
- [ ] Tab cycles through plots
- [ ] Only one plot focused at a time
