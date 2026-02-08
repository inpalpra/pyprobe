# Sub-Agent 2: In-Place Axis Editing

## Overview

You are implementing in-place min/max editing for PyProbe axes. This allows users to double-click on the first or last tick label to directly edit the axis range, following LabVIEW conventions.

## Goal

Create an inline text editor that appears when users double-click axis tick labels.

## Constitution Compliance

| § | Principle | How This Task Complies |
|---|-----------|------------------------|
| 1 | Gesture over Config | Double-click directly on tick, no dialogs |
| 2 | Acknowledge Every Action | Editor appears immediately, value commits visually |
| 12 | Tool Disappears | Inline edit feels natural, not like a separate UI |

## Constraints

- **No dialogs or popups** (Constitution §1)
- Enter commits, Escape cancels
- Editing min/max auto-pins the axis
- Must integrate with `AxisController` from Sub-Agent 1

---

## Reference Files

| File | Purpose |
|------|---------|
| [waveform_plot.py](file:///Users/ppal/repos/pyprobe/pyprobe/plots/waveform_plot.py) | Plot widget to modify |
| [axis_controller.py](file:///Users/ppal/repos/pyprobe/pyprobe/plots/axis_controller.py) | Pin state (from Sub-Agent 1) |
| [graph-palette-requirements.md](file:///Users/ppal/repos/pyprobe/plans/implementation/m2.5/graph-palette/graph-palette-requirements.md) | R2: Explicit Min/Max requirements |

---

## Deliverables

### 1. New File: `pyprobe/gui/axis_editor.py`

```python
"""
Inline editor for axis min/max values.

Appears over the tick label when user double-clicks.
Commits on Enter, cancels on Escape.
"""

from PyQt6.QtWidgets import QLineEdit, QWidget
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QValidator, QDoubleValidator


class AxisEditor(QLineEdit):
    """Inline editor for axis min/max values.
    
    Usage:
        editor = AxisEditor(parent)
        editor.show_at(x, y, current_value)
        editor.value_committed.connect(on_new_value)
    
    Signals:
        value_committed(float): New value accepted
        editing_cancelled(): Escape pressed or focus lost
    """
    
    value_committed = pyqtSignal(float)
    editing_cancelled = pyqtSignal()
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._setup_ui()
        self._original_value: float = 0.0
    
    def _setup_ui(self) -> None:
        """Configure the editor appearance."""
        # Compact size
        self.setFixedWidth(80)
        self.setFixedHeight(24)
        
        # Dark theme style matching PyProbe
        self.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a2e;
                color: #00ffff;
                border: 1px solid #00ffff;
                border-radius: 3px;
                padding: 2px 4px;
                font-family: Menlo, monospace;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 2px solid #00ffff;
            }
        """)
        
        # Numeric validation
        validator = QDoubleValidator()
        validator.setNotation(QDoubleValidator.Notation.ScientificNotation)
        self.setValidator(validator)
        
        # Start hidden
        self.hide()
    
    def show_at(self, x: int, y: int, initial_value: float) -> None:
        """Show editor at position with initial value.
        
        Args:
            x: X position (widget coordinates)
            y: Y position (widget coordinates)
            initial_value: Current axis value to display
        """
        self._original_value = initial_value
        
        # Format value nicely
        if abs(initial_value) < 0.001 or abs(initial_value) > 10000:
            text = f"{initial_value:.3e}"
        else:
            text = f"{initial_value:.4g}"
        
        self.setText(text)
        self.move(x, y)
        self.show()
        self.setFocus()
        self.selectAll()
    
    def keyPressEvent(self, event) -> None:
        """Handle Enter and Escape keys."""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self._commit()
        elif event.key() == Qt.Key.Key_Escape:
            self._cancel()
        else:
            super().keyPressEvent(event)
    
    def focusOutEvent(self, event) -> None:
        """Cancel on focus loss."""
        super().focusOutEvent(event)
        if self.isVisible():
            self._cancel()
    
    def _commit(self) -> None:
        """Commit the current value."""
        try:
            value = float(self.text())
            self.hide()
            self.value_committed.emit(value)
        except ValueError:
            # Invalid number - flash red briefly
            self.setStyleSheet(self.styleSheet().replace("#00ffff", "#ff4444"))
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(200, lambda: self.setStyleSheet(
                self.styleSheet().replace("#ff4444", "#00ffff")
            ))
    
    def _cancel(self) -> None:
        """Cancel editing and hide."""
        self.hide()
        self.editing_cancelled.emit()
```

### 2. New File: `pyprobe/plots/editable_axis.py`

```python
"""
Custom PyQtGraph AxisItem with double-click editing support.
"""

import pyqtgraph as pg
from PyQt6.QtCore import pyqtSignal, QPointF
from PyQt6.QtWidgets import QGraphicsSceneMouseEvent


class EditableAxisItem(pg.AxisItem):
    """AxisItem that emits signals for double-click on tick labels.
    
    Signals:
        edit_min_requested(float): Double-click on first tick
        edit_max_requested(float): Double-click on last tick
    """
    
    edit_min_requested = pyqtSignal(float)
    edit_max_requested = pyqtSignal(float)
    
    def __init__(self, orientation, **kwargs):
        super().__init__(orientation, **kwargs)
        self.setAcceptHoverEvents(True)
    
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handle double-click on axis."""
        pos = event.pos()
        
        # Get current axis range
        view_range = self.linkedView().viewRange()
        if self.orientation == 'bottom' or self.orientation == 'top':
            axis_range = view_range[0]  # X range
        else:
            axis_range = view_range[1]  # Y range
        
        min_val, max_val = axis_range
        
        # Determine if click is near min or max tick
        # Based on position within the axis item bounds
        bounds = self.boundingRect()
        
        if self.orientation == 'bottom' or self.orientation == 'top':
            # Horizontal axis
            relative_pos = pos.x() / bounds.width()
            if relative_pos < 0.2:  # Left 20% = min
                self.edit_min_requested.emit(min_val)
            elif relative_pos > 0.8:  # Right 20% = max
                self.edit_max_requested.emit(max_val)
        else:
            # Vertical axis
            relative_pos = pos.y() / bounds.height()
            if relative_pos > 0.8:  # Bottom 20% = min (Y is inverted)
                self.edit_min_requested.emit(min_val)
            elif relative_pos < 0.2:  # Top 20% = max
                self.edit_max_requested.emit(max_val)
        
        event.accept()
```

### 3. Modify: `pyprobe/plots/waveform_plot.py`

```python
# At top, add imports:
from pyprobe.gui.axis_editor import AxisEditor
from .editable_axis import EditableAxisItem

# In _setup_ui(), replace PlotItem creation with custom axes:
# Before:
# self._plot_item = pg.PlotItem()

# After:
x_axis = EditableAxisItem('bottom')
y_axis = EditableAxisItem('left')
self._plot_item = pg.PlotItem(axisItems={'bottom': x_axis, 'left': y_axis})

# Connect axis edit signals:
x_axis.edit_min_requested.connect(lambda v: self._start_axis_edit('x', 'min', v))
x_axis.edit_max_requested.connect(lambda v: self._start_axis_edit('x', 'max', v))
y_axis.edit_min_requested.connect(lambda v: self._start_axis_edit('y', 'min', v))
y_axis.edit_max_requested.connect(lambda v: self._start_axis_edit('y', 'max', v))

# Create axis editor (shared):
self._axis_editor = AxisEditor(self)
self._editing_axis: str = None
self._editing_bound: str = None
self._axis_editor.value_committed.connect(self._on_axis_value_committed)

# Add methods:
def _start_axis_edit(self, axis: str, bound: str, current_value: float) -> None:
    """Start inline editing of axis min/max.
    
    Args:
        axis: 'x' or 'y'
        bound: 'min' or 'max'
        current_value: Current value at that bound
    """
    self._editing_axis = axis
    self._editing_bound = bound
    
    # Position editor near the relevant axis
    if axis == 'x':
        y_pos = self.height() - 40  # Near bottom
        x_pos = 20 if bound == 'min' else self.width() - 100
    else:
        x_pos = 10  # Near left
        y_pos = self.height() - 40 if bound == 'min' else 20
    
    self._axis_editor.show_at(x_pos, y_pos, current_value)

def _on_axis_value_committed(self, value: float) -> None:
    """Handle committed axis value edit."""
    if self._editing_axis is None:
        return
    
    # Get current range
    view_box = self._plot_item.getViewBox()
    x_range, y_range = view_box.viewRange()
    
    # Update the appropriate bound
    if self._editing_axis == 'x':
        if self._editing_bound == 'min':
            self._plot_item.setXRange(value, x_range[1], padding=0)
        else:
            self._plot_item.setXRange(x_range[0], value, padding=0)
        # Pin X axis
        self._axis_controller.set_pinned('x', True)
    else:
        if self._editing_bound == 'min':
            self._plot_item.setYRange(value, y_range[1], padding=0)
        else:
            self._plot_item.setYRange(y_range[0], value, padding=0)
        # Pin Y axis
        self._axis_controller.set_pinned('y', True)
    
    self._editing_axis = None
    self._editing_bound = None
```

---

## Unit Tests

Create file: `tests/test_axis_editor.py`

```python
"""Unit tests for AxisEditor."""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from pyprobe.gui.axis_editor import AxisEditor


@pytest.fixture(scope="module")
def app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def editor(app):
    """Create an AxisEditor for testing."""
    return AxisEditor()


class TestAxisEditorDisplay:
    """Test AxisEditor display functionality."""
    
    def test_initially_hidden(self, editor):
        assert not editor.isVisible()
    
    def test_show_at_makes_visible(self, editor):
        editor.show_at(10, 10, 1.5)
        assert editor.isVisible()
    
    def test_show_at_sets_text(self, editor):
        editor.show_at(10, 10, 123.456)
        assert "123" in editor.text()
    
    def test_scientific_notation_for_small(self, editor):
        editor.show_at(10, 10, 0.000123)
        assert "e" in editor.text().lower()
    
    def test_scientific_notation_for_large(self, editor):
        editor.show_at(10, 10, 12345678.0)
        assert "e" in editor.text().lower()


class TestAxisEditorCommit:
    """Test value commit functionality."""
    
    def test_enter_commits_value(self, editor):
        committed_values = []
        editor.value_committed.connect(lambda v: committed_values.append(v))
        
        editor.show_at(10, 10, 1.0)
        editor.setText("42.5")
        QTest.keyClick(editor, Qt.Key.Key_Return)
        
        assert 42.5 in committed_values
        assert not editor.isVisible()
    
    def test_escape_cancels(self, editor):
        cancelled = []
        editor.editing_cancelled.connect(lambda: cancelled.append(True))
        
        editor.show_at(10, 10, 1.0)
        editor.setText("999")
        QTest.keyClick(editor, Qt.Key.Key_Escape)
        
        assert len(cancelled) == 1
        assert not editor.isVisible()


class TestAxisEditorValidation:
    """Test input validation."""
    
    def test_invalid_input_does_not_commit(self, editor):
        committed_values = []
        editor.value_committed.connect(lambda v: committed_values.append(v))
        
        editor.show_at(10, 10, 1.0)
        editor.setText("not a number")
        QTest.keyClick(editor, Qt.Key.Key_Return)
        
        # Should still be visible (didn't commit)
        # Note: actual behavior may flash red
        assert len(committed_values) == 0
```

---

## Manual Verification

1. **Double-click first tick → edit min**:
   - Probe an array variable
   - Double-click on the leftmost X tick label
   - Editor appears with current min value
   - Type new value (e.g., "-10")
   - Press Enter
   - Verify X range starts at -10, lock icon appears

2. **Double-click last tick → edit max**:
   - Double-click on rightmost X tick
   - Change to larger value
   - Verify range extends, still pinned

3. **Escape cancels**:
   - Start editing
   - Press Escape
   - Verify no change, editor hidden

4. **Y axis editing**:
   - Double-click on bottom/top Y ticks
   - Verify Y range editable

---

## Success Criteria

- [ ] Double-click on first tick starts editing min
- [ ] Double-click on last tick starts editing max
- [ ] Editor appears inline (no dialog)
- [ ] Enter commits value and pins axis
- [ ] Escape cancels without change
- [ ] Invalid input (non-numeric) is rejected
- [ ] Lock icon appears after commit
- [ ] All unit tests pass
