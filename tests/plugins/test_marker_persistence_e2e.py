import os
import pytest
import numpy as np
from PyQt6.QtCore import Qt
from pyprobe.gui.main_window import MainWindow
from pyprobe.core.probe_persistence import get_sidecar_path
from pyprobe.core.anchor import ProbeAnchor

def test_marker_persistence_e2e(qtbot, tmp_path):
    # 1. Setup a dummy script with enough content for AST
    script_path = str(tmp_path / "test_script.py")
    with open(script_path, "w") as f:
        f.write("x = [1, 2, 3]\n")
    
    # 2. Open MainWindow and load script
    window = MainWindow(script_path=script_path)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    
    # 3. Add a probe for 'x' on line 1
    vars_on_line = window._code_viewer.ast_locator.get_all_variables_on_line(1)
    assert len(vars_on_line) > 0
    var_loc = vars_on_line[0]
    
    anchor = ProbeAnchor(
        file=os.path.abspath(script_path),
        line=1,
        col=var_loc.col_start,
        symbol="x",
        func="",
        is_assignment=True
    )
    
    window._on_probe_requested(anchor)
    qtbot.wait(100)
    
    # 4. Add a marker to the panel
    assert anchor in window._probe_controller.probe_panels
    panel = window._probe_controller.probe_panels[anchor][-1]
    
    # Ensure plot widget is created (may need data)
    panel.update_data(np.array([1, 2, 3]), "array_1d")
    
    store = panel._plot._marker_store
    m0 = store.add_marker(trace_key=0, x=1.5, y=2.0)
    assert m0.id == "m0"
    
    # 5. Save settings (should happen automatically now)
    # window._save_probe_settings()
    
    # Wait for the signal-triggered save to finish (it's synchronous but let's give it a tiny bit)
    qtbot.wait(100)
    
    # Verify sidecar exists
    sidecar = get_sidecar_path(script_path)
    assert sidecar.exists()
    
    # 6. Close window and open a NEW one
    window.close()
    
    # Clear global state for fresh start
    from pyprobe.plots.marker_model import MarkerStore
    MarkerStore._global_used_ids.clear()
    MarkerStore._all_stores.clear()
    
    window2 = MainWindow(script_path=script_path)
    qtbot.addWidget(window2)
    window2.show()
    
    # 7. Verify marker is restored
    # Inject data to window2 to trigger plot widget creation and marker injection
    def inject_data_window2():
        if anchor in window2._probe_controller.probe_panels:
            p2 = window2._probe_controller.probe_panels[anchor][-1]
            p2.update_data(np.array([1, 2, 3]), "array_1d")
            return True
        return False
        
    qtbot.waitUntil(inject_data_window2, timeout=2000)
    
    def check_restored():
        p2 = window2._probe_controller.probe_panels[anchor][-1]
        if not hasattr(p2, '_plot') or p2._plot is None:
            return False
        # The restoration logic injects markers into the store
        if not hasattr(p2._plot, '_marker_store') or p2._plot._marker_store is None:
             return False
        return len(p2._plot._marker_store.get_markers()) == 1
        
    qtbot.waitUntil(check_restored, timeout=5000)
    
    panel2 = window2._probe_controller.probe_panels[anchor][-1]
    m_restored = panel2._plot._marker_store.get_markers()[0]
    assert m_restored.id == "m0"
    assert m_restored.x == 1.5
    assert m_restored.y == 2.5 # Snapped to curve [1, 2, 3] at x=1.5
