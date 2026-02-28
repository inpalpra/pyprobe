"""Phase 3.4: Overlay system GUI tests.

Verifies adding/removing overlay curves on WaveformWidget.
"""

import numpy as np
import pytest
from PyQt6.QtGui import QColor

from pyprobe.plugins.builtins.waveform import WaveformWidget
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D


@pytest.fixture
def waveform(qtbot, qapp, probe_color):
    """Create a WaveformWidget with initial data."""
    w = WaveformWidget("primary", probe_color)
    qtbot.addWidget(w)
    w.resize(600, 400)
    w.show()
    qapp.processEvents()
    w.update_data(np.array([1, 2, 3, 4, 5], dtype=float), DTYPE_ARRAY_1D)
    qapp.processEvents()
    yield w
    w.close()
    w.deleteLater()
    qapp.processEvents()


class TestOverlayAdd:
    def test_add_overlay_curve(self, waveform, qapp):
        """Adding an overlay creates an additional curve."""
        if not hasattr(waveform, 'add_overlay'):
            pytest.skip("add_overlay not yet implemented on WaveformWidget")

        overlay_data = np.array([5, 4, 3, 2, 1], dtype=float)
        waveform.add_overlay("secondary", overlay_data, QColor("#ff00ff"))
        qapp.processEvents()

        # Should have overlay curves
        assert hasattr(waveform, '_overlay_curves')
        assert "secondary" in waveform._overlay_curves

    def test_overlay_data_correct(self, waveform, qapp):
        """Overlay curve contains the correct data."""
        if not hasattr(waveform, 'add_overlay'):
            pytest.skip("add_overlay not yet implemented on WaveformWidget")

        overlay_data = np.array([10, 20, 30], dtype=float)
        waveform.add_overlay("overlay1", overlay_data, QColor("#ff00ff"))
        qapp.processEvents()

        curve = waveform._overlay_curves["overlay1"]
        _, y = curve.getData()
        np.testing.assert_allclose(y, [10, 20, 30])


class TestOverlayRemove:
    def test_remove_overlay(self, waveform, qapp):
        """Removing an overlay removes its curve."""
        if not hasattr(waveform, 'add_overlay'):
            pytest.skip("add_overlay not yet implemented on WaveformWidget")

        waveform.add_overlay("to_remove", np.array([1, 2, 3], dtype=float), QColor("#ff00ff"))
        qapp.processEvents()
        assert "to_remove" in waveform._overlay_curves

        waveform.remove_overlay("to_remove")
        qapp.processEvents()
        assert "to_remove" not in waveform._overlay_curves


class TestGetPlotDataWithOverlays:
    def test_get_plot_data_includes_overlays(self, waveform, qapp):
        """get_plot_data() includes overlay curves."""
        if not hasattr(waveform, 'add_overlay'):
            pytest.skip("add_overlay not yet implemented on WaveformWidget")

        waveform.add_overlay("ref", np.array([9, 8, 7], dtype=float), QColor("#ff00ff"))
        qapp.processEvents()

        plot_data = waveform.get_plot_data()
        overlay_entries = [d for d in plot_data if d.get('is_overlay')]
        assert len(overlay_entries) >= 1
