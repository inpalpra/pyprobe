# Sub-Agent 02: In-Place Axis Editing

## Context

You are implementing in-place min/max editing for PyProbe axes. This allows users to double-click on the first or last tick label to edit the axis range.

## Goal

Create an inline text editor that appears when users double-click axis tick labels, following LabVIEW conventions.

## Constraints

- No dialogs or popups (Constitution §1)
- Enter commits, Escape cancels
- Editing min/max auto-pins the axis
- Must integrate with existing AxisController

## Inputs

- Double-click on first tick → edit min value
- Double-click on last tick → edit max value

## Expected Outputs

### File: `pyprobe/gui/axis_editor.py`

```python
from PyQt6.QtWidgets import QLineEdit, QWidget
from PyQt6.QtCore import pyqtSignal

class AxisEditor(QLineEdit):
    """Inline editor for axis min/max values.
    
    Appears over the tick label when activated.
    Commits on Enter, cancels on Escape.
    """
    
    # Signals
    value_committed = pyqtSignal(float)  # New value accepted
    editing_cancelled = pyqtSignal()      # Escape pressed
    
    def __init__(self, parent: QWidget = None):
        ...
    
    def show_at(self, x: int, y: int, initial_value: float) -> None:
        """Show editor at position with initial value."""
        ...
    
    def keyPressEvent(self, event) -> None:
        """Handle Enter and Escape."""
        ...
```

### Modifications to `WaveformPlot`

Add event handlers for double-click on axis items:

```python
def _on_axis_double_clicked(self, axis: str, position: str):
    """Handle double-click on axis tick label.
    
    Args:
        axis: 'x' or 'y'
        position: 'first' or 'last' (min or max)
    """
    ...
```

## Hit-Test Logic

Critical: Must correctly identify which tick was clicked.

```
Double-click event
    ↓
Check if event.pos() is on AxisItem
    ↓
Identify which tick label was hit
    ↓
If first tick → edit min
If last tick → edit max
Otherwise → ignore
```

## Integration Points

1. Subclass or extend PyQtGraph `AxisItem` to intercept double-clicks
2. Connect to AxisController to set pin state on commit
3. Call `PlotItem.setXRange()` or `setYRange()` after commit

## Test Plan

1. Unit test: `test_axis_editor.py`
   - Create AxisEditor widget
   - Verify initial value display
   - Simulate Enter key → verify value_committed signal
   - Simulate Escape → verify editing_cancelled signal

2. Manual test:
   - Probe array variable
   - Double-click on leftmost X tick label
   - Type new min value, press Enter
   - Verify axis range updates and lock icon appears

## Success Criteria

- [ ] Double-click on first tick starts editing min
- [ ] Double-click on last tick starts editing max
- [ ] Enter commits value and pins axis
- [ ] Escape cancels without change
- [ ] Invalid input (non-numeric) is rejected gracefully
