import pytest
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor
from pyprobe.gui.main_window import MainWindow
from pyprobe.core.anchor import ProbeAnchor

@pytest.fixture
def main_window(qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    mw.show()
    return mw

def test_equation_plotting_flow(main_window, qtbot):
    # 1. Add an equation
    eq = main_window._equation_manager.add_equation("tr0 * 2")
    eq_id = eq.id
    
    # 2. Simulate data for tr0
    main_window._latest_trace_data["tr0"] = np.array([1, 2, 3])
    main_window._equation_manager.evaluate_all(main_window._latest_trace_data)
    
    # 3. Request plot
    main_window._on_equation_plot_requested(eq_id)
    
    # 4. Verify panel created
    assert eq_id in main_window._equation_to_panels
    panel = main_window._equation_to_panels[eq_id][0]
    assert panel.window_id == "w0"
    
    # 5. Verify plot widget is correct type (Waveform since result is 1D array)
    from pyprobe.plugins.builtins.waveform import WaveformWidget
    assert isinstance(panel._plot, WaveformWidget)
    
    # 6. Verify data rendered
    # We can check if the curve has data
    plot_data = panel.get_plot_data()
    # For WaveformWidget, get_plot_data returns a list of curves or dict with y
    if isinstance(plot_data, list):
        assert np.array_equal(plot_data[0]['y'], [2, 4, 6])
    else:
        assert np.array_equal(plot_data['y'], [2, 4, 6])

def test_equation_plot_deduplication(main_window, qtbot):
    eq = main_window._equation_manager.add_equation("tr0")
    eq_id = eq.id
    
    main_window._on_equation_plot_requested(eq_id)
    assert len(main_window._equation_to_panels[eq_id]) == 1
    
    # Click again
    main_window._on_equation_plot_requested(eq_id)
    assert len(main_window._equation_to_panels[eq_id]) == 1
