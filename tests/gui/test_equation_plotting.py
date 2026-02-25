import pytest
import numpy as np
from PyQt6.QtGui import QColor
from pyprobe.gui.main_window import MainWindow
from pyprobe.core.anchor import ProbeAnchor

def test_equation_overlay_logic(qapp):
    win = MainWindow()
    # Mock some data
    anchor = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")
    win._probe_registry.add_probe(anchor)
    win._latest_trace_data["tr0"] = np.array([1, 2, 3])
    
    # Create an equation
    eq = win._equation_manager.add_equation("tr0 * 10")
    win._equation_manager.evaluate_all(win._latest_trace_data)
    
    assert np.array_equal(eq.result, np.array([10, 20, 30]))
    
    # Simulate a panel
    panel = win._probe_container.create_panel("x", "array_1d", anchor=anchor, trace_id="tr0")
    
    # Simulate drop
    win._on_equation_overlay_requested(panel, "eq0")
    
    assert panel in win._equation_to_panels["eq0"]
    
    # Verify update logic doesn't crash
    win._update_equation_plots()
    
    # Check if overlay curve was created (WaveformWidget specific)
    # This reaches deep into internals
    plot = panel._plot
    assert hasattr(plot, "_overlay_curves")
    assert "eq0_rhs" in plot._overlay_curves
    
    win.close()

def test_equation_new_window_logic(qapp):
    win = MainWindow()
    eq = win._equation_manager.add_equation("1 + 2")
    win._equation_manager.evaluate_all({})
    
    # Simulate 'Plot' click
    win._on_equation_plot_requested("eq0")
    
    assert "eq0" in win._equation_to_panels
    panels = win._equation_to_panels["eq0"]
    assert len(panels) == 1
    assert panels[0].var_name == "eq0"
    
    win.close()
