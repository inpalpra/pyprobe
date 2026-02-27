import pytest
from PyQt6.QtWidgets import QApplication
from pyprobe.gui.main_window import MainWindow
from pyprobe.report.step_recorder import StepRecorder
from pyprobe.core.anchor import ProbeAnchor

@pytest.fixture
def win(qtbot):
    win = MainWindow()
    qtbot.addWidget(win)
    return win

def test_legend_toggle_records_step_integration(qtbot, win):
    """Integration: simulate legend click on a real panel and verify StepRecorder captures it."""
    anchor = ProbeAnchor(file="test.py", line=10, col=2, symbol="signal_i")
    
    # 1. Add a probe to create a panel
    win._on_probe_requested(anchor)
    panel = win._probe_container.get_panel(anchor=anchor)
    assert panel is not None
    
    # Force a real WaveformWidget by providing some 2D data
    import numpy as np
    panel.update_data(np.zeros((2, 1024)), "array_2d")
    
    # Wait for plot widget to be created and legend to be populated
    plot = panel._plot
    assert plot is not None
    qtbot.wait_until(lambda: plot._legend is not None and len(plot._legend.items) > 0, timeout=1000)
    
    # 2. Start recording
    win._step_recorder.start()
    
    # 3. Simulate legend click
    # RemovableLegendItem stores (sample, label) in self.items
    # We can trigger _toggle_visibility(item) directly if we find it
    assert len(plot._legend.items) > 0
    item, label = plot._legend.items[0]
    
    # In RemovableLegendItem, item is the ItemSample
    plot._legend._toggle_visibility(item)
    
    # 4. Stop recording and check steps
    steps = win._step_recorder.stop()
    
    descriptions = [s.description for s in steps]
    found = any("Toggled visibility of" in d for d in descriptions)
    
    assert found, f"Expected step 'Toggled visibility of...' in {descriptions}"

def test_lens_switch_does_not_emit_toggle_event(qtbot, win):
    """Verify that automated visibility changes during lens switching are NOT recorded."""
    anchor = ProbeAnchor(file="test.py", line=10, col=2, symbol="signal_i")
    
    # 1. Add a probe
    win._on_probe_requested(anchor)
    panel = win._probe_container.get_panel(anchor=anchor)
    assert panel is not None
    
    # 2. Start recording
    win._step_recorder.start()
    
    # 3. Simulate lens switch
    # This will recreate the plot widget and its legend
    panel._on_lens_changed("Real & Imag")
    
    # 4. Stop recording and check steps
    steps = win._step_recorder.stop()
    
    descriptions = [s.description for s in steps]
    found = any("Toggled visibility of" in d for d in descriptions)
    
    assert not found, f"Spurious 'Toggled visibility of...' step found after lens switch: {descriptions}"
