
import pytest
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor
from pyprobe.gui.probe_panel import ProbePanel
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.report.step_recorder import StepRecorder
from pyprobe.gui.probe_controller import ProbeController
from unittest.mock import MagicMock
import pyqtgraph as pg

@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])

def test_view_adjustment_debouncing(app):
    # Setup
    anchor = ProbeAnchor(file="test.py", line=10, col=1, symbol="var")
    color = QColor("#00ffff")
    recorder = StepRecorder()
    
    panel = ProbePanel(anchor=anchor, color=color, dtype="float64", window_id="w0")
    
    # Wire recorder
    panel.view_adjusted.connect(
        lambda a=anchor, wid=panel.window_id: recorder.record(f"Adjusted view in window {wid} ({a.identity_label()})")
    )
    
    recorder.start()
    
    # Emit multiple times rapidly
    panel._on_manual_view_change([True, True])
    panel._on_manual_view_change([True, True])
    panel._on_manual_view_change([True, True])
    
    # Wait for less than debounce interval (500ms)
    time.sleep(0.1)
    app.processEvents()
    assert len(recorder.steps) == 0
    
    # Wait for remaining debounce interval
    time.sleep(0.5)
    app.processEvents()
    
    assert len(recorder.steps) == 1
    assert "Adjusted view" in recorder.steps[0].description
    
    recorder.stop()
