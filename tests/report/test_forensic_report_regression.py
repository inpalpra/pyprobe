
import pytest
import numpy as np
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.gui.probe_panel import ProbePanel
from pyprobe.gui.probe_registry import ProbeRegistry
from pyprobe.gui.probe_controller import ProbeController
from pyprobe.report.formatter import ReportFormatter
from pyprobe.report.session_snapshot import SessionStateCollector
from pyprobe.report.report_model import BugReport
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D, DTYPE_ARRAY_COMPLEX

@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])

@pytest.fixture
def controller(qtbot):
    # Setup real registry and container but mock code_viewer/gutter for isolation
    registry = ProbeRegistry()
    from pyprobe.gui.panel_container import ProbePanelContainer
    container = ProbePanelContainer()
    
    class MockObj:
        def __getattr__(self, name): return lambda *args, **kwargs: None
        
    ctrl = ProbeController(
        registry=registry,
        container=container,
        code_viewer=MockObj(),
        gutter=MockObj(),
        get_ipc=lambda: None,
        get_is_running=lambda: False
    )
    return ctrl

def test_no_legend_duplication_on_overlay(qapp, controller, qtbot):
    """
    REGRESSION: Case 1 - Verify adding an overlay does NOT 
    cause the overlay trace to appear twice in the legend.
    """
    anchor_main = ProbeAnchor(file="test.py", line=60, col=8, symbol="sig_main")
    anchor_ov = ProbeAnchor(file="test.py", line=46, col=4, symbol="sig_ov")
    
    # 1. Add primary panel
    panel = controller.add_probe(anchor_main)
    panel.update_data(np.random.randn(500), DTYPE_ARRAY_1D)
    
    # 2. Add overlay
    controller.handle_overlay_requested(panel, anchor_ov)
    controller.forward_overlay_data(anchor_ov, {'value': np.random.randn(500), 'dtype': DTYPE_ARRAY_1D})
    
    # 3. Inspect legend entries
    legend = panel._plot._legend
    labels = [label.text if hasattr(label, 'text') else str(label) for _, label in legend.items]
    
    # Find tr1: sig_ov (or whatever trace ID was assigned)
    ov_id = controller._registry.get_trace_id(anchor_ov)
    ov_label = f"{ov_id}: sig_ov"
    
    ov_count = labels.count(ov_label)
    assert ov_count == 1, f"Overlay trace '{ov_label}' should appear exactly once in legend, found {ov_count}. Labels: {labels}"

def test_fft_overlay_legend_support(qapp, controller, qtbot):
    """
    REGRESSION: Case 2 - Verify that FFT lens correctly supports overlays 
    in the legend and uses forensic nomenclature in the report.
    """
    anchor_main = ProbeAnchor(file="test.py", line=60, col=8, symbol="sig_complex")
    anchor_ov = ProbeAnchor(file="test.py", line=46, col=4, symbol="sig_real")
    
    # 1. Add primary panel with FFT lens
    panel = controller.add_probe(anchor_main, lens_name="FFT Mag & Phase")
    panel.update_data(np.random.randn(500) + 1j*np.random.randn(500), DTYPE_ARRAY_COMPLEX)
    
    # Wait for lens switch to complete
    qtbot.waitUntil(lambda: panel.current_lens == "FFT Mag & Phase", timeout=1000)
    
    # 2. Add overlay
    controller.handle_overlay_requested(panel, anchor_ov)
    controller.forward_overlay_data(anchor_ov, {'value': np.random.randn(500), 'dtype': DTYPE_ARRAY_1D})
    
    # Wait for overlay to render
    qtbot.waitUntil(lambda: hasattr(panel._plot, '_legend') and panel._plot._legend is not None, timeout=1000)
    
    # 3. Verify legend contains overlay
    legend = panel._plot._legend
    labels = [label.text if hasattr(label, 'text') else str(label) for _, label in legend.items]
    
    ov_id = controller._registry.get_trace_id(anchor_ov)
    ov_label = f"{ov_id}: sig_real"
    assert ov_label in labels, f"Overlay '{ov_label}' missing from FFT legend. Found: {labels}"
    
    # 4. Verify Forensic Report Nomenclature
    entry = panel.get_report_entry(controller._registry, is_docked=True)
    report = BugReport(description="FFT Forensic Test", baseline_state=SessionStateCollector(
        lambda:[], lambda:[], lambda:[], lambda: [entry]).collect())
    
    formatter = ReportFormatter()
    output = formatter.render(report)
    
    # Primary should have fft components
    main_id = controller._registry.get_trace_id(anchor_main)
    assert f"plotted:  {main_id}  [{main_id}.fft_mag_db, {main_id}.fft_angle_deg]" in output
    # Overlay should be listed
    assert f"overlaid: {ov_id}  [{ov_id}.val]" in output
