"""Phase 2.1: Waveform plot visual correctness tests.

Verifies what users actually SEE on waveform plots by inspecting
pyqtgraph widget internals (curve data, labels, stats).
"""

import numpy as np
import pytest
from PyQt6.QtGui import QColor

from pyprobe.plugins.builtins.waveform import WaveformWidget, WaveformPlugin
from pyprobe.core.data_classifier import (
    DTYPE_ARRAY_1D, DTYPE_ARRAY_2D, DTYPE_WAVEFORM_REAL
)


@pytest.fixture
def waveform(qtbot, qapp, probe_color):
    """Create a WaveformWidget for testing."""
    w = WaveformWidget("test_signal", probe_color)
    qtbot.addWidget(w)
    w.resize(600, 400)
    w.show()
    qapp.processEvents()
    yield w
    w.close()
    w.deleteLater()
    qapp.processEvents()


class TestWaveform1DData:
    def test_update_1d_array(self, waveform):
        """1D array data appears on curve."""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        waveform.update_data(data, DTYPE_ARRAY_1D)

        x, y = waveform._curves[0].getData()
        np.testing.assert_allclose(y, [1, 2, 3, 4, 5])

    def test_update_replaces_previous(self, waveform):
        """Second update replaces the first data."""
        waveform.update_data(np.array([1, 2, 3]), DTYPE_ARRAY_1D)
        waveform.update_data(np.array([10, 20, 30]), DTYPE_ARRAY_1D)

        _, y = waveform._curves[0].getData()
        np.testing.assert_allclose(y, [10, 20, 30])

    def test_none_is_ignored(self, waveform):
        """Passing None does not crash."""
        waveform.update_data(None, DTYPE_ARRAY_1D)
        # Should still have initial empty/no-data state

    def test_list_input_converted(self, waveform):
        """Plain Python list is accepted."""
        waveform.update_data([7, 8, 9], DTYPE_ARRAY_1D)
        _, y = waveform._curves[0].getData()
        np.testing.assert_allclose(y, [7, 8, 9])


class TestWaveform2DData:
    def test_2d_array_curve_count(self, waveform):
        """2D array creates one curve per row."""
        data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        waveform.update_data(data, DTYPE_ARRAY_2D, shape=data.shape)
        assert len(waveform._curves) == 3

    def test_2d_array_row_data(self, waveform):
        """Each curve contains the correct row data."""
        data = np.array([[10, 20], [30, 40]])
        waveform.update_data(data, DTYPE_ARRAY_2D, shape=data.shape)

        _, y0 = waveform._curves[0].getData()
        _, y1 = waveform._curves[1].getData()
        np.testing.assert_allclose(y0, [10, 20])
        np.testing.assert_allclose(y1, [30, 40])

    def test_2d_to_1d_reduces_curves(self, waveform):
        """Switching from 2D to 1D reduces curve count."""
        data_2d = np.array([[1, 2], [3, 4], [5, 6]])
        waveform.update_data(data_2d, DTYPE_ARRAY_2D, shape=data_2d.shape)
        assert len(waveform._curves) == 3

        data_1d = np.array([10, 20, 30])
        waveform.update_data(data_1d, DTYPE_ARRAY_1D)
        assert len(waveform._curves) == 1


class TestWaveformLabels:
    def test_name_label(self, waveform):
        """Name label matches variable name."""
        assert waveform._name_label.text() == "test_signal"

    def test_stats_label_after_update(self, waveform):
        """Stats label shows min/max/mean after data update."""
        data = np.array([2.0, 4.0, 6.0, 8.0, 10.0])
        waveform.update_data(data, DTYPE_ARRAY_1D)

        text = waveform._stats_label.text()
        assert "Min:" in text
        assert "Max:" in text
        assert "Mean:" in text
        # Min=2, Max=10, Mean=6
        assert "2" in text
        assert "10" in text
        assert "6" in text

    def test_stats_initial_state(self, waveform):
        """Stats label shows placeholder before data."""
        assert "--" in waveform._stats_label.text()


class TestWaveformDownsampling:
    def test_small_array_not_downsampled(self, waveform):
        """Arrays under MAX_DISPLAY_POINTS pass through unchanged."""
        data = np.arange(100, dtype=float)
        waveform.update_data(data, DTYPE_ARRAY_1D)

        _, y = waveform._curves[0].getData()
        assert len(y) == 100

    def test_large_array_downsampled(self, waveform):
        """Arrays over MAX_DISPLAY_POINTS are downsampled."""
        data = np.arange(10000, dtype=float)
        waveform.update_data(data, DTYPE_ARRAY_1D)

        _, y = waveform._curves[0].getData()
        assert len(y) <= waveform.MAX_DISPLAY_POINTS

    def test_downsample_preserves_minmax(self, waveform):
        """Min-max downsampling preserves extreme values."""
        data = np.zeros(10000)
        data[3333] = 100.0   # spike
        data[6666] = -50.0   # dip
        downsampled = waveform.downsample(data)
        assert np.max(downsampled) >= 100.0
        assert np.min(downsampled) <= -50.0


class TestWaveformStruct:
    def test_waveform_dict_uses_time_vector(self, waveform):
        """Serialized waveform struct uses t0+dt as x-axis."""
        wf_data = {
            '__dtype__': DTYPE_WAVEFORM_REAL,
            'samples': [1.0, 2.0, 3.0, 4.0],
            'scalars': [0.0, 0.5],  # t0=0, dt=0.5
        }
        waveform.update_data(wf_data, DTYPE_WAVEFORM_REAL)

        x, y = waveform._curves[0].getData()
        np.testing.assert_allclose(y, [1, 2, 3, 4])
        np.testing.assert_allclose(x, [0.0, 0.5, 1.0, 1.5])


class TestWaveformPlugin:
    def test_can_handle_array_1d(self):
        plugin = WaveformPlugin()
        assert plugin.can_handle(DTYPE_ARRAY_1D, None)

    def test_can_handle_array_2d(self):
        plugin = WaveformPlugin()
        assert plugin.can_handle(DTYPE_ARRAY_2D, None)

    def test_cannot_handle_scalar(self):
        plugin = WaveformPlugin()
        assert not plugin.can_handle('scalar', None)

    def test_create_widget(self, qtbot, qapp, probe_color):
        plugin = WaveformPlugin()
        w = plugin.create_widget("var", probe_color)
        qtbot.addWidget(w)
        assert isinstance(w, WaveformWidget)
        w.close()
        w.deleteLater()
        qapp.processEvents()

    def test_update_delegates(self, waveform):
        plugin = WaveformPlugin()
        data = np.array([5, 10, 15])
        plugin.update(waveform, data, DTYPE_ARRAY_1D)
        _, y = waveform._curves[0].getData()
        np.testing.assert_allclose(y, [5, 10, 15])
