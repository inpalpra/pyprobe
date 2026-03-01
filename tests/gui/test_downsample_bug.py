"""
Tests for the downsampling pipeline in WaveformWidget.

Level 1: X-axis correctness after min-max decimation.
Level 2: Zoom-responsive re-rendering (raw data at high zoom).
"""

import numpy as np
import pytest
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QTimer

from pyprobe.plugins.builtins.waveform import WaveformWidget
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D


@pytest.fixture
def probe_color():
    return QColor("#00ffcc")


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


# ── Level 1: X-axis correctness ──────────────────────────────

class TestDownsampleXAxis:
    """Verify x-axis maps back to original sample indices after downsampling."""

    def test_short_array_x_axis_is_correct(self, waveform):
        """Short arrays (< MAX_DISPLAY_POINTS) have correct x-axis."""
        data = np.sin(np.linspace(0, 10 * np.pi, 1000))
        waveform.update_data(data, DTYPE_ARRAY_1D)

        plot_data = waveform.get_plot_data()
        x = np.array(plot_data[0]['x'])
        assert len(x) == 1000
        np.testing.assert_allclose(x, np.arange(1000))

    def test_long_array_x_axis_spans_full_range(self, waveform):
        """Downsampled x-axis must span [0, ~N-1], not [0, ~4999]."""
        N = 16000
        data = np.sin(np.linspace(0, 10 * np.pi, N))
        waveform.update_data(data, DTYPE_ARRAY_1D)

        plot_data = waveform.get_plot_data()
        x = np.array(plot_data[0]['x'])
        y = np.array(plot_data[0]['y'])

        assert len(y) <= waveform.MAX_DISPLAY_POINTS
        assert x[-1] > 5000, (
            f"x-axis max is {x[-1]} but should be close to {N-1}"
        )

    def test_downsampled_y_monotonic_for_ramp(self, waveform):
        """Monotonic ramp must stay monotonic after downsample + x-fix."""
        N = 16000
        data = np.linspace(0, 100, N)
        waveform.update_data(data, DTYPE_ARRAY_1D)

        plot_data = waveform.get_plot_data()
        y = np.array(plot_data[0]['y'])
        diffs = np.diff(y)
        sign_changes = np.sum(diffs[:-1] * diffs[1:] < 0)
        assert sign_changes == 0, (
            f"Monotonic signal zigzags {sign_changes} times after downsampling"
        )


# ── Level 2: Zoom-responsive re-rendering ────────────────────

class TestZoomResponsiveDownsampling:
    """Verify that zooming in shows raw data, zooming out re-downsamples."""

    def _zoom_and_extract(self, waveform, qapp, x_min, x_max):
        """Programmatically zoom and wait for debounced re-render."""
        ac = waveform.axis_controller
        if ac:
            ac.set_pinned('x', True)
        plot_item = waveform._plot_widget.getPlotItem()
        plot_item.setXRange(x_min, x_max, padding=0)
        qapp.processEvents()
        # Pump the event loop long enough for the 50ms debounce timer to fire
        import time
        deadline = time.monotonic() + 0.2  # 200ms is plenty for 50ms timer
        while time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.01)
        qapp.processEvents()
        return waveform.get_plot_data()

    def test_zoom_in_shows_raw_data(self, waveform, qapp):
        """Zooming in to < MAX_DISPLAY_POINTS samples shows raw (undownsampled) data."""
        N = 16000
        data = np.sin(np.linspace(0, 10 * np.pi, N))
        waveform.update_data(data, DTYPE_ARRAY_1D)

        # Zoom into a 1000-sample window (< 5000 threshold)
        plot_data = self._zoom_and_extract(waveform, qapp, 7000, 8000)
        x = np.array(plot_data[0]['x'])
        y = np.array(plot_data[0]['y'])

        # Should show ~1000 raw samples, not downsampled
        assert len(y) >= 900, f"Expected ~1000 raw points, got {len(y)}"
        assert len(y) <= 1100, f"Expected ~1000 raw points, got {len(y)}"

        # x-range should be within [7000, 8000]
        assert x[0] >= 6999, f"x starts at {x[0]}, expected >= 7000"
        assert x[-1] <= 8001, f"x ends at {x[-1]}, expected <= 8000"

        # Y values should match the original data exactly (full resolution)
        i_min = int(x[0])
        i_max = int(x[-1]) + 1
        expected_y = data[i_min:i_max]
        np.testing.assert_allclose(y, expected_y, atol=1e-10)

    def test_zoom_out_redownsamples(self, waveform, qapp):
        """Zooming back out from raw view re-downsamples."""
        N = 16000
        data = np.sin(np.linspace(0, 10 * np.pi, N))
        waveform.update_data(data, DTYPE_ARRAY_1D)

        # Zoom in first
        self._zoom_and_extract(waveform, qapp, 7000, 8000)

        # Zoom back out to full range
        plot_data = self._zoom_and_extract(waveform, qapp, 0, N)
        y = np.array(plot_data[0]['y'])

        # Should be downsampled again (≤ MAX_DISPLAY_POINTS)
        assert len(y) <= waveform.MAX_DISPLAY_POINTS, (
            f"After zoom-out, got {len(y)} points (expected ≤ {waveform.MAX_DISPLAY_POINTS})"
        )

    def test_intermediate_zoom_redownsamples(self, waveform, qapp):
        """Zooming to an intermediate range (> MAX_DISPLAY_POINTS visible) re-downsamples."""
        N = 16000
        data = np.sin(np.linspace(0, 10 * np.pi, N))
        waveform.update_data(data, DTYPE_ARRAY_1D)

        # Zoom to 6000-sample range (> 5000 threshold, still needs downsampling)
        plot_data = self._zoom_and_extract(waveform, qapp, 2000, 8000)
        x = np.array(plot_data[0]['x'])
        y = np.array(plot_data[0]['y'])

        # Should be downsampled but with better resolution than full view
        assert len(y) <= waveform.MAX_DISPLAY_POINTS
        # x-range should be within the zoomed region
        assert x[0] >= 1999, f"x starts at {x[0]}, expected >= 2000"
        assert x[-1] <= 8001, f"x ends at {x[-1]}, expected <= 8000"
