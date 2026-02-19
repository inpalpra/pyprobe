"""Phase 3.2: Probe panel keyboard shortcut tests.

Verifies X, Y, R, Escape keys toggle axis pins and reset toolbar.
"""

import numpy as np
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtTest import QTest

from pyprobe.gui.probe_panel import ProbePanel
from pyprobe.gui.plot_toolbar import InteractionMode
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D


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


class TestXKeyPin:
    def test_x_key_toggles_x_pin(self, panel, qapp):
        """X key toggles x_pinned on axis controller."""
        ac = panel._plot.axis_controller
        assert ac is not None
        assert not ac.x_pinned

        QTest.keyPress(panel, Qt.Key.Key_X)
        qapp.processEvents()
        assert ac.x_pinned

    def test_x_key_twice_unpins(self, panel, qapp):
        """X key pressed twice returns to unpinned."""
        ac = panel._plot.axis_controller
        QTest.keyPress(panel, Qt.Key.Key_X)
        QTest.keyPress(panel, Qt.Key.Key_X)
        qapp.processEvents()
        assert not ac.x_pinned


class TestYKeyPin:
    def test_y_key_toggles_y_pin(self, panel, qapp):
        """Y key toggles y_pinned."""
        ac = panel._plot.axis_controller
        assert not ac.y_pinned

        QTest.keyPress(panel, Qt.Key.Key_Y)
        qapp.processEvents()
        assert ac.y_pinned


class TestRKeyReset:
    def test_r_key_unpins_both(self, panel, qapp):
        """R key resets both axes to unpinned."""
        ac = panel._plot.axis_controller
        # Pin both
        ac.set_pinned('x', True)
        ac.set_pinned('y', True)

        QTest.keyPress(panel, Qt.Key.Key_R)
        qapp.processEvents()

        assert not ac.x_pinned
        assert not ac.y_pinned


class TestEscapeKey:
    def test_escape_resets_toolbar_mode(self, panel, qapp):
        """Escape key resets toolbar mode to POINTER."""
        # Change mode away from POINTER
        panel._toolbar.set_mode(InteractionMode.PAN)
        qapp.processEvents()
        assert panel._toolbar.current_mode == InteractionMode.PAN

        QTest.keyPress(panel, Qt.Key.Key_Escape)
        qapp.processEvents()
        assert panel._toolbar.current_mode == InteractionMode.POINTER
