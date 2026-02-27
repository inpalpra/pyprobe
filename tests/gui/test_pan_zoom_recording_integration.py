
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor
from pyprobe.gui.probe_panel import ProbePanel
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.report.step_recorder import StepRecorder
from pyprobe.gui.probe_controller import ProbeController
from unittest.mock import MagicMock

@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])

def test_pan_zoom_reset_recording(app):
    # Setup
    anchor = ProbeAnchor(file="test.py", line=10, col=1, symbol="var")
    color = QColor("#00ffff")
    recorder = StepRecorder()
    
    # Mock dependencies for controller
    container = MagicMock()
    # Ensure create_probe_panel returns a real ProbePanel so we can emit signals
    panel = ProbePanel(anchor=anchor, color=color, dtype="float64", window_id="w0")
    container.create_probe_panel.return_value = panel
    
    registry = MagicMock()
    registry.is_full.return_value = False
    registry.add_probe.return_value = color
    registry.get_trace_id.return_value = "tr0"
    
    controller = ProbeController(
        registry=registry,
        container=container,
        code_viewer=MagicMock(),
        gutter=MagicMock(),
        get_ipc=lambda: None,
        get_is_running=lambda: False
    )
    
    # Wire recorder like MainWindow does
    controller.panel_interaction_mode_changed.connect(
        lambda a, wid, mode: recorder.record(f"Changed tool to {mode} in window {wid} ({a.identity_label()})")
    )
    controller.panel_view_reset_triggered.connect(
        lambda a, wid: recorder.record(f"Reset view in window {wid} ({a.identity_label()})")
    )
    controller.panel_view_adjusted.connect(
        lambda a, wid: recorder.record(f"Adjusted view in window {wid} ({a.identity_label()})")
    )
    
    # Create the probe (this connects signals in controller)
    controller.add_probe(anchor)
    
    recorder.start()
    
    # 1. Test Mode Change
    panel.interaction_mode_changed.emit("PAN")
    
    # 2. Test Reset
    panel.view_reset_triggered.emit()
    
    # 3. Test View Adjusted
    panel.view_adjusted.emit()
    
    steps = recorder.stop()
    
    descriptions = [s.description for s in steps]
    assert any("Changed tool to PAN in window w0" in d for d in descriptions)
    assert any("Reset view in window w0" in d for d in descriptions)
    assert any("Adjusted view in window w0" in d for d in descriptions)

    print("\nVerified steps:")
    for d in descriptions:
        print(f"  - {d}")
