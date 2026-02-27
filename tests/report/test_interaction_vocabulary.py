import pytest
from PyQt6.QtCore import QObject, pyqtSignal
from pyprobe.report.step_recorder import StepRecorder
from pyprobe.core.anchor import ProbeAnchor

class MockController(QObject):
    panel_legend_moved = pyqtSignal(object, str)
    panel_view_interaction_triggered = pyqtSignal(object, str, str)

def test_interaction_vocabulary_capture():
    recorder = StepRecorder()
    anchor = ProbeAnchor(file="test.py", line=10, col=5, symbol="sig")
    
    controller = MockController()
    
    # Connect signals to recorder using the same lambdas as in MainWindow
    recorder.connect_signal(
        controller.panel_legend_moved,
        lambda a, wid: f"Moved legend in window {wid} ({a.identity_label()})")
    recorder.connect_signal(
        controller.panel_view_interaction_triggered,
        lambda a, wid, desc: f"{desc} in window {wid} ({a.identity_label()})")
    
    recorder.start()
    
    # 1. Test Legend Movement
    controller.panel_legend_moved.emit(anchor, "w0")
    assert recorder.steps[-1].description == "Moved legend in window w0 (sig @ test.py:10:5)"
    
    # 2. Test Tool-based Pan
    controller.panel_view_interaction_triggered.emit(anchor, "w0", "Panned view using tool")
    assert recorder.steps[-1].description == "Panned view using tool in window w0 (sig @ test.py:10:5)"
    
    # 3. Test Direct Axis Drag
    controller.panel_view_interaction_triggered.emit(anchor, "w1", "Panned Horizontal axis directly")
    assert recorder.steps[-1].description == "Panned Horizontal axis directly in window w1 (sig @ test.py:10:5)"
    
    # 4. Test Direct Axis Wheel
    controller.panel_view_interaction_triggered.emit(anchor, "w1", "Scrolled Vertical axis directly")
    assert recorder.steps[-1].description == "Scrolled Vertical axis directly in window w1 (sig @ test.py:10:5)"
