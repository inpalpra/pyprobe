import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from pyprobe.gui.probe_panel import ProbePanel
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D
import numpy as np


@pytest.fixture
def panel(qapp, probe_color):
    """Create a ProbePanel with data for keyboard testing."""
    anchor = ProbeAnchor(
        file="/tmp/test.py", line=1, col=0,
        symbol="sig", func="main",
    )
    p = ProbePanel(anchor, probe_color, DTYPE_ARRAY_1D)
    p.resize(600, 400)
    p.show()
    qapp.processEvents()
    # Feed data so plot is properly initialized
    p.update_data(np.array([1, 2, 3, 4, 5], dtype=float), DTYPE_ARRAY_1D)
    qapp.processEvents()
    # Give focus
    p.setFocus()
    qapp.processEvents()
    return p


class TestPKeyPark:
    def test_p_key_emits_park_requested(self, panel, qapp):
        """P key emits the park_requested signal."""
        emitted = False
        def on_park_requested():
            nonlocal emitted
            emitted = True
            
        panel.park_requested.connect(on_park_requested)
        
        QTest.keyPress(panel, Qt.Key.Key_P)
        qapp.processEvents()
        
        assert emitted, "park_requested signal should have been emitted when 'P' key was pressed"
