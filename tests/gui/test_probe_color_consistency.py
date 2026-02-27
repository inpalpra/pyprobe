
import pytest
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.gui.probe_controller import ProbeController
from pyprobe.gui.probe_registry import ProbeRegistry
from pyprobe.gui.panel_container import ProbePanelContainer
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D

class MockCodeViewer:
    def set_probe_active(self, anchor, color): pass
    def remove_probe(self, anchor): pass
    def update_probe_color(self, anchor, color): pass

class MockGutter:
    def set_probed_line(self, line, color): pass
    def clear_probed_line(self, line): pass

@pytest.fixture
def controller(qtbot):
    registry = ProbeRegistry()
    container = ProbePanelContainer()
    code_viewer = MockCodeViewer()
    gutter = MockGutter()
    
    # Mocking necessary methods for ProbeController
    get_ipc = lambda: None
    get_is_running = lambda: False
    
    ctrl = ProbeController(
        registry=registry,
        container=container,
        code_viewer=code_viewer,
        gutter=gutter,
        get_ipc=get_ipc,
        get_is_running=get_is_running
    )
    return ctrl

def test_color_consistency_new_panel(controller, qtbot):
    anchor = ProbeAnchor(file="test.py", line=10, col=5, symbol="sig")
    
    # 1. Add first panel
    panel1 = controller.add_probe(anchor)
    color1 = panel1._color
    
    # 2. Add second panel for same anchor (e.g. via Ctrl+click)
    panel2 = controller.add_probe(anchor)
    color2 = panel2._color
    
    assert color1 == color2, "Second panel should use same color as first"

def test_color_propagation_across_panels(controller, qtbot):
    anchor = ProbeAnchor(file="test.py", line=10, col=5, symbol="sig")
    panel1 = controller.add_probe(anchor)
    panel2 = controller.add_probe(anchor)
    
    # Initialize both with array data to switch from ScalarHistory to Waveform
    panel1.update_data([1, 2, 3], DTYPE_ARRAY_1D)
    panel2.update_data([1, 2, 3], DTYPE_ARRAY_1D)
    
    # 3. Change color on panel1
    new_color = QColor("#ff0000")
    panel1.color_changed.emit(anchor, new_color)
    
    assert panel1._color == new_color
    assert panel2._color == new_color, "Color change should propagate to second panel"
    
    # Verify widget color updated too
    assert panel2._plot._color == new_color

def test_color_consistency_overlay(controller, qtbot):
    anchor_main = ProbeAnchor(file="test.py", line=10, col=5, symbol="main")
    anchor_ov = ProbeAnchor(file="test.py", line=20, col=5, symbol="ov")
    
    panel_main = controller.add_probe(anchor_main)
    panel_ov = controller.add_probe(anchor_ov)
    
    # Switch to Waveform for overlay support
    panel_main.update_data([1, 2, 3], DTYPE_ARRAY_1D)
    
    ov_color = panel_ov._color
    
    # 4. Request overlay of 'ov' onto 'main'
    controller.handle_overlay_requested(panel_main, anchor_ov)
    
    # 5. Send data to trigger overlay rendering
    payload = {'value': [1, 2, 3], 'dtype': DTYPE_ARRAY_1D}
    controller.forward_overlay_data(anchor_ov, payload)
    
    # Find the overlay curve in panel_main's plot
    plot = panel_main._plot
    overlay_key = f"ov_rhs" # rhs because not an assignment in this mock
    assert hasattr(plot, '_overlay_curves')
    assert overlay_key in plot._overlay_curves
    curve = plot._overlay_curves[overlay_key]
    
    # Check curve color
    actual_color = curve.opts['pen'].color().name()
    expected_color = ov_color.name()
    assert actual_color == expected_color, f"Overlay curve should use probe's assigned color. Expected {expected_color}, got {actual_color}"

def test_color_consistency_overlay_after_change(controller, qtbot):
    anchor_main = ProbeAnchor(file="test.py", line=10, col=5, symbol="main")
    anchor_ov = ProbeAnchor(file="test.py", line=20, col=5, symbol="ov")
    
    panel_main = controller.add_probe(anchor_main)
    panel_ov = controller.add_probe(anchor_ov)
    
    # Switch to Waveform
    panel_main.update_data([1, 2, 3], DTYPE_ARRAY_1D)
    
    # 6. Change color of overlay probe
    new_color = QColor("#00ff00")
    panel_ov.color_changed.emit(anchor_ov, new_color)
    
    # 7. Add overlay
    controller.handle_overlay_requested(panel_main, anchor_ov)
    controller.forward_overlay_data(anchor_ov, {'value': [1, 2, 3], 'dtype': DTYPE_ARRAY_1D})
    
    plot = panel_main._plot
    assert hasattr(plot, '_overlay_curves')
    curve = plot._overlay_curves["ov_rhs"]
    assert curve.opts['pen'].color() == new_color, "Overlay added after color change should use NEW color"

def test_color_consistency_constellation_overlay(controller, qtbot):
    from pyprobe.core.data_classifier import DTYPE_ARRAY_COMPLEX
    anchor_main = ProbeAnchor(file="test.py", line=10, col=5, symbol="main")
    anchor_ov = ProbeAnchor(file="test.py", line=20, col=5, symbol="ov")
    
    panel_main = controller.add_probe(anchor_main)
    panel_ov = controller.add_probe(anchor_ov)
    
    # Switch to Constellation
    panel_main.update_data([1+1j, 2+2j], DTYPE_ARRAY_COMPLEX)
    
    ov_color = panel_ov._color
    
    # Add overlay
    controller.handle_overlay_requested(panel_main, anchor_ov)
    controller.forward_overlay_data(anchor_ov, {'value': [1+1j, 2+2j], 'dtype': DTYPE_ARRAY_COMPLEX})
    
    plot = panel_main._plot
    assert hasattr(plot, '_overlay_scatters')
    scatter = plot._overlay_scatters["ov_rhs"]
    
    # Check brush color
    assert scatter.opts['brush'].color().name() == ov_color.name(), "Constellation overlay should use probe color"
