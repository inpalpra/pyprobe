import pytest
from PyQt6.QtWidgets import QLineEdit
from pyprobe.gui.marker_manager import MarkerManager
from pyprobe.gui.probe_panel import ProbePanel
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D
from pyprobe.plots.marker_model import MarkerStore

@pytest.fixture(autouse=True)
def clean_markers():
    MarkerStore._global_used_ids.clear()
    MarkerStore._all_stores.clear()
    yield
    MarkerStore._global_used_ids.clear()
    MarkerStore._all_stores.clear()

def test_marker_manager_filters_by_active_view(qtbot, sample_anchor, probe_color):
    # 1. Setup panel and manager
    panel = ProbePanel(sample_anchor, probe_color, DTYPE_ARRAY_1D)
    qtbot.addWidget(panel)
    panel.show()
    
    manager = MarkerManager.show_instance()
    qtbot.addWidget(manager)
    
    # 2. Add marker to Waveform
    panel._plot._marker_store.add_marker(0, 10.0, 1.0)
    qtbot.waitUntil(lambda: manager.table.rowCount() == 1)
    
    # 3. Switch to FFT
    panel._on_lens_changed("FFT Mag (dB) / Angle (deg)")
    
    # 4. Verify MarkerManager table is EMPTY (since Waveform markers are parked)
    qtbot.waitUntil(lambda: manager.table.rowCount() == 0)
    
    # 5. Add marker to FFT
    panel._plot._marker_store.add_marker(0, 5.0, 0.0)
    qtbot.waitUntil(lambda: manager.table.rowCount() == 1)
    
    # 6. Switch back to Waveform
    panel._on_lens_changed("Waveform")
    
    # 7. Verify MarkerManager table shows Waveform marker again
    def check_m0():
        if manager.table.rowCount() != 1:
            return False
        id_lbl = manager.table.cellWidget(0, 1)
        return id_lbl is not None and "m0" in id_lbl.text()
        
    qtbot.waitUntil(check_m0, timeout=1000)

def test_marker_manager_multi_panel_filtering(qtbot, sample_anchor_factory, probe_color):
    # 1. Setup two panels and manager
    anchor1 = sample_anchor_factory(symbol="var1")
    anchor2 = sample_anchor_factory(symbol="var2")
    
    panel1 = ProbePanel(anchor1, probe_color, DTYPE_ARRAY_1D)
    panel2 = ProbePanel(anchor2, probe_color, DTYPE_ARRAY_1D)
    qtbot.addWidget(panel1)
    qtbot.addWidget(panel2)
    panel1.show()
    panel2.show()
    
    manager = MarkerManager.show_instance()
    qtbot.addWidget(manager)
    
    # 2. Add marker to both
    panel1._plot._marker_store.add_marker(0, 1.0, 1.0) # m0
    panel2._plot._marker_store.add_marker(0, 2.0, 2.0) # m1
    
    qtbot.waitUntil(lambda: manager.table.rowCount() == 2)
    
    # 3. Switch panel1 to FFT
    panel1._on_lens_changed("FFT Mag (dB) / Angle (deg)")
    
    # 4. Verify manager only shows panel2's marker (m1)
    qtbot.waitUntil(lambda: manager.table.rowCount() == 1)
    id_lbl = manager.table.cellWidget(0, 1)
    assert "m1" in id_lbl.text()
    
    # 5. Switch back panel1 to Waveform
    panel1._on_lens_changed("Waveform")
    
    # 6. Verify manager shows both again
    qtbot.waitUntil(lambda: manager.table.rowCount() == 2)
