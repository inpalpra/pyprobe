# TDD Workflow Example: PyQt6 E2E

This document provides a concrete example of the "Red-Green-Refactor" cycle for a PyQt6 GUI feature in PyProbe.

## 1. Task Definition
**Task:** Implement a "Mute" button on the `WaveformWidget` that hides the curve without removing the data.

## 2. Red Phase: Write Failing Test
Create `tests/gui/test_waveform_mute.py`:

```python
import pytest
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from pyprobe.plugins.builtins.waveform import WaveformWidget

@pytest.fixture
def widget(qapp):
    w = WaveformWidget("test", "blue")
    w.show()
    qapp.processEvents()
    return w

def test_mute_button_hides_curve(widget, qapp):
    # 1. Setup data
    widget.update_data(np.array([1, 2, 3]), "array_1d")
    curve = widget._curves[0]
    assert curve.isVisible()

    # 2. Trigger Mute (assuming a button exists)
    # Since it doesn't exist yet, we might call the method we plan to add
    widget.set_muted(True)
    qapp.processEvents()

    # 3. Assert Failure
    assert not curve.isVisible()
```

**Run Test:**
```bash
uv run pytest tests/gui/test_waveform_mute.py
# Result: AttributeError: 'WaveformWidget' object has no attribute 'set_muted'
```

## 3. Green Phase: Implementation
Implement the minimum code in `pyprobe/plugins/builtins/waveform.py`:

```python
class WaveformWidget(BasePlotWidget):
    # ...
    def set_muted(self, muted: bool):
        for curve in self._curves:
            curve.setVisible(not muted)
```

**Run Test:**
```bash
uv run pytest tests/gui/test_waveform_mute.py
# Result: 1 passed
```

## 4. Refactor Phase
Improve the implementation (e.g., add a UI button that calls `set_muted`). Update the test to use `QTest.mouseClick` on the actual button.

```python
def test_mute_ui_click(widget, qapp):
    widget.update_data(np.array([1, 2, 3]), "array_1d")
    
    # Click the new mute button
    QTest.mouseClick(widget.mute_button, Qt.MouseButton.LeftButton)
    qapp.processEvents()
    
    assert not widget._curves[0].isVisible()
```
