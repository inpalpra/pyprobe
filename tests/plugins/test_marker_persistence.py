import numpy as np
import pytest
from PyQt6.QtGui import QColor
from pyprobe.plots.marker_model import MarkerStore
from pyprobe.gui.probe_panel import ProbePanel
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D
from pyprobe.plugins.builtins.waveform import WaveformWidget

@pytest.fixture(autouse=True)
def clean_markers():
    MarkerStore._global_used_ids.clear()
    MarkerStore._all_stores.clear()
    yield
    MarkerStore._global_used_ids.clear()
    MarkerStore._all_stores.clear()

def test_markers_preserved_during_switch(qtbot, sample_anchor, probe_color):
    # 1. Setup panel with Waveform lens
    panel = ProbePanel(sample_anchor, probe_color, DTYPE_ARRAY_1D)
    qtbot.addWidget(panel)
    panel.show()
    qtbot.waitExposed(panel)
    
    # 2. Add a marker to Waveform view
    assert isinstance(panel._plot, WaveformWidget)
    store = panel._plot._marker_store
    m0 = store.add_marker(trace_key=0, x=10.0, y=1.0)
    assert len(store.get_markers()) == 1
    
    # 3. Switch to another lens
    panel._on_lens_changed("FFT Mag (dB) / Angle (deg)")
    qtbot.wait(50)
    
    # 4. Switch back to Waveform
    panel._on_lens_changed("Waveform")
    qtbot.wait(50)
    
    # 5. Verify marker is RESTORED
    new_store = panel._plot._marker_store
    assert len(new_store.get_markers()) == 1, "Markers were not restored!"
    m_restored = new_store.get_markers()[0]
    assert m_restored.id == "m0"
    assert m_restored.x == 10.0
    assert m_restored.y == 1.0

def test_markers_unique_ids_across_views(qtbot, sample_anchor, probe_color):
    panel = ProbePanel(sample_anchor, probe_color, DTYPE_ARRAY_1D)
    qtbot.addWidget(panel)
    panel.show()
    
    # 1. Add m0 to Waveform
    panel._plot._marker_store.add_marker(0, 10.0, 1.0) # gets m0
    
    # 2. Switch to FFT
    panel._on_lens_changed("FFT Mag (dB) / Angle (deg)")
    
    # 3. Add marker to FFT
    m_fft = panel._plot._marker_store.add_marker(0, 5.0, 0.0)
    
    # 4. Verify it gets m1, NOT m0
    assert m_fft.id == "m1", f"Expected m1, got {m_fft.id}"
    
    # 5. Switch back to Waveform
    panel._on_lens_changed("Waveform")
    
    # 6. Verify Waveform still has m0 and FFT still has m1 (in vault)
    assert len(panel._plot._marker_store.get_markers()) == 1
    assert panel._plot._marker_store.get_markers()[0].id == "m0"
