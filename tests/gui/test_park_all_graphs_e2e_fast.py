"""Tests for parking graphs.

Fast Tests Implementation:
This file uses the 'megascript' strategy to execute all GUI scenarios sequentially
in a single `MainWindow` instance at the module level. Individual test functions
then assert against the captured state dictionary to achieve massive speedups
by avoiding repeated QApplication/MainWindow tearups.
"""

import pytest
import numpy as np
import os
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

pytestmark = pytest.mark.skipif("GITHUB_ACTIONS" in os.environ, reason="Requires GUI head for accurate geometry rendering")

from pyprobe.gui.main_window import MainWindow
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.data_classifier import (
    DTYPE_SCALAR,
    DTYPE_ARRAY_1D,
    DTYPE_ARRAY_COMPLEX,
    DTYPE_ARRAY_2D
)

_STATE = {}

def _create_and_park_graph(win, qapp, symbol: str, data, dtype, shape=None, lens=None):
    """Helper to create a probe, feed it data, park it via 'P' key, and capture state."""
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
    
    panel_list = win._probe_panels.get(anchor, [])
    panel = panel_list[0] if panel_list else None
    
    lens_found = False
    if lens is not None and panel is not None:
        texts = [panel._lens_dropdown.itemText(i) for i in range(panel._lens_dropdown.count())]
        if lens in texts:
            lens_found = True
            panel._on_lens_changed(lens)
            qapp.processEvents()

    if panel is not None:
        panel.setFocus()
        qapp.processEvents()
        
        QTest.keyPress(panel, Qt.Key.Key_P)
        qapp.processEvents()

    _STATE[symbol] = {
        "panel_created": panel is not None,
        "lens_found": lens_found if lens is not None else True,
        "panel_hidden": not panel.isVisible() if panel else False,
        "in_parked_panels": anchor in win._probe_container._parked_panels,
        "in_dock_bar": anchor.identity_label() in win._dock_bar._items,
        "dock_bar_visible": win._dock_bar.isVisible(),
    }


@pytest.fixture(scope="module", autouse=True)
def _run_all_scenarios(qapp):
    win = MainWindow()
    win.resize(1200, 800)
    win.show()
    qapp.processEvents()
    
    _create_and_park_graph(win, qapp, "scalar_val", 42, DTYPE_SCALAR)
    _create_and_park_graph(win, qapp, "waveform_1d", np.array([1.0, 2.0, 3.0]), DTYPE_ARRAY_1D)
    _create_and_park_graph(win, qapp, "complex_1d", np.array([1+1j, 2-2j, -1+1j]), DTYPE_ARRAY_COMPLEX)
    _create_and_park_graph(win, qapp, "array_2d", np.array([[1.0, 2.0], [3.0, 4.0]]), DTYPE_ARRAY_2D, shape=(2, 2))
    
    # For complex lenses, we create a dummy first
    dummy_anchor = ProbeAnchor(file="/tmp/test_park.py", line=1, col=0, symbol="dummy", func="main")
    win._on_probe_requested(dummy_anchor)
    payload = {'anchor': dummy_anchor.to_dict(), 'value': np.array([1+1j]), 'dtype': DTYPE_ARRAY_COMPLEX}
    win._on_probe_value(payload)
    qapp.processEvents()
    
    dummy_panel = win._probe_panels.get(dummy_anchor, [None])[0]
    if dummy_panel:
        lenses = [dummy_panel._lens_dropdown.itemText(i) for i in range(dummy_panel._lens_dropdown.count())]
    else:
        lenses = []
        
    _STATE["complex_lenses"] = lenses
    for i, lens in enumerate(lenses):
        symbol = f"complex_lens_{i}"
        data = np.array([1+1j, 2-2j, -1+1j])
        _create_and_park_graph(win, qapp, symbol, data, DTYPE_ARRAY_COMPLEX, lens=lens)
        
    win.close()
    qapp.processEvents()

class TestParkAllGraphsE2E:
    def _assert_parked(self, symbol):
        state = _STATE[symbol]
        assert state["panel_created"], f"{symbol} panel should be created"
        if "lens_found" in state:
            assert state["lens_found"], f"Lens requested for {symbol} not found"
        assert state["panel_hidden"], f"{symbol} panel should be hidden after parking"
        assert state["in_parked_panels"], f"{symbol} anchor should be in parked set"
        assert state["in_dock_bar"], f"{symbol} should have an item in the dock bar"
        assert state["dock_bar_visible"], "Dock bar should be visible after parking a panel"

    def test_park_scalar_graph(self):
        self._assert_parked("scalar_val")

    def test_park_waveform_graph(self):
        self._assert_parked("waveform_1d")

    def test_park_constellation_graph(self):
        self._assert_parked("complex_1d")

    def test_park_2d_array_graph(self):
        self._assert_parked("array_2d")

    def test_park_all_complex_lenses(self):
        lenses = _STATE.get("complex_lenses", [])
        assert len(lenses) > 0, "No lenses found for complex graph"
        for i, lens in enumerate(lenses):
            symbol = f"complex_lens_{i}"
            self._assert_parked(symbol)
