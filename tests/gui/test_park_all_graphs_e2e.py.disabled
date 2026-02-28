import pytest
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

# Skip all tests in this file if running in CI since they require real geometry rendering
import os
pytestmark = pytest.mark.skipif("GITHUB_ACTIONS" in os.environ, reason="Requires GUI head for accurate geometry rendering")

from pyprobe.gui.main_window import MainWindow
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.data_classifier import (
    DTYPE_SCALAR,
    DTYPE_ARRAY_1D,
    DTYPE_ARRAY_COMPLEX,
    DTYPE_ARRAY_2D
)

@pytest.fixture
def win(qapp):
    """Create a MainWindow for testing."""
    window = MainWindow()
    window.resize(1200, 800)
    window.show()
    qapp.processEvents()
    yield window
    window.close()
    qapp.processEvents()


def _create_and_park_graph(win, qapp, symbol: str, data, dtype, shape=None, lens=None):
    """Helper to create a probe, feed it data, park it via 'P' key, and verify."""
    anchor = ProbeAnchor(file="/tmp/test_park.py", line=1, col=0, symbol=symbol, func="main")
    
    # 1. Add probe
    win._on_probe_requested(anchor)
    qapp.processEvents()
    
    # 2. Feed data
    payload = {
        'anchor': anchor.to_dict(),
        'value': data,
        'dtype': dtype,
    }
    if shape is not None:
        payload['shape'] = shape
        
    win._on_probe_value(payload)
    qapp.processEvents()
    
    # Ensure panel was created
    assert anchor in win._probe_panels
    panel_list = win._probe_panels[anchor]
    assert len(panel_list) > 0
    panel = panel_list[0]
    
    # Switch lens if requested
    if lens is not None:
        # Check if the lens actually exists in the dropdown to avoid silent failures
        texts = [panel._lens_dropdown.itemText(i) for i in range(panel._lens_dropdown.count())]
        assert lens in texts, f"Lens '{lens}' not found in dropdown. Available: {texts}"
        panel._on_lens_changed(lens)
        qapp.processEvents()

    # Ensure it is visible initially
    assert panel.isVisible()
    
    # Give panel focus
    panel.setFocus()
    qapp.processEvents()
    
    # 3. Press 'P' key
    QTest.keyPress(panel, Qt.Key.Key_P)
    qapp.processEvents()
    
    # 4. Verify parking state
    # Panel should be hidden
    assert not panel.isVisible(), f"{symbol} panel should be hidden after parking"
    
    # Panel should be in container's parked list
    assert anchor in win._probe_container._parked_panels, f"{symbol} anchor should be in parked set"
    
    # Panel should be in dock bar
    dock_bar_item = anchor.identity_label()
    assert dock_bar_item in win._dock_bar._items, f"{symbol} should have an item in the dock bar"
    assert win._dock_bar.isVisible(), "Dock bar should be visible after parking a panel"


class TestParkAllGraphsE2E:
    def test_park_scalar_graph(self, win, qapp):
        """Test parking a scalar graph (ScalarHistoryWidget)."""
        _create_and_park_graph(win, qapp, "scalar_val", 42, DTYPE_SCALAR)

    def test_park_waveform_graph(self, win, qapp):
        """Test parking a waveform graph (WaveformWidget)."""
        data = np.array([1.0, 2.0, 3.0])
        _create_and_park_graph(win, qapp, "waveform_1d", data, DTYPE_ARRAY_1D)

    def test_park_constellation_graph(self, win, qapp):
        """Test parking a constellation graph (ComplexRIWidget / ConstellationWidget)."""
        data = np.array([1+1j, 2-2j, -1+1j])
        _create_and_park_graph(win, qapp, "complex_1d", data, DTYPE_ARRAY_COMPLEX)

    def test_park_2d_array_graph(self, win, qapp):
        """Test parking a 2D array graph (WaveformWidget / ImageWidget)."""
        data = np.array([[1.0, 2.0], [3.0, 4.0]])
        _create_and_park_graph(win, qapp, "array_2d", data, DTYPE_ARRAY_2D, shape=(2, 2))

    def test_park_all_complex_lenses(self, win, qapp):
        """Test parking a complex graph with every available lens."""
        # Use a dummy probe to find available lenses
        dummy_anchor = ProbeAnchor(file="/tmp/test_park.py", line=1, col=0, symbol="dummy", func="main")
        win._on_probe_requested(dummy_anchor)
        payload = {'anchor': dummy_anchor.to_dict(), 'value': np.array([1+1j]), 'dtype': DTYPE_ARRAY_COMPLEX}
        win._on_probe_value(payload)
        qapp.processEvents()
        
        dummy_panel = win._probe_panels[dummy_anchor][0]
        lenses = [dummy_panel._lens_dropdown.itemText(i) for i in range(dummy_panel._lens_dropdown.count())]
        
        # Test each lens with a fresh probe
        for i, lens in enumerate(lenses):
            symbol = f"complex_lens_{i}"
            data = np.array([1+1j, 2-2j, -1+1j])
            _create_and_park_graph(win, qapp, symbol, data, DTYPE_ARRAY_COMPLEX, lens=lens)
