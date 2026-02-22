"""
Tests for complex plot downsample & zoom-responsive re-rendering.

Covers ComplexRIWidget (Real & Imag), ComplexMAWidget (Mag & Phase),
and SingleCurveWidget (Log Mag, Linear Mag, Phase).
"""

import numpy as np
import pytest
import time
from PyQt6.QtGui import QColor

from pyprobe.plugins.builtins.complex_plots import (
    ComplexRIWidget, ComplexMAWidget, SingleCurveWidget,
    ComplexRIPlugin, ComplexMAPlugin, LogMagPlugin,
)
from pyprobe.core.data_classifier import DTYPE_ARRAY_COMPLEX


@pytest.fixture
def probe_color():
    return QColor("#00ffcc")


def _pump_events(qapp, duration_ms=200):
    """Pump Qt event loop long enough for the 50ms debounce timer."""
    deadline = time.monotonic() + duration_ms / 1000.0
    while time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    qapp.processEvents()


def _zoom_and_extract(widget, qapp, x_min, x_max):
    """Set x-range, wait for re-render, extract plot data."""
    plot_item = widget._plot_widget.getPlotItem()
    plot_item.setXRange(x_min, x_max, padding=0)
    _pump_events(qapp)
    return widget.get_plot_data()


# ── ComplexRIWidget ──────────────────────────────────────────

class TestComplexRIXAxis:
    """Real & Imag downsampling preserves x-axis."""

    @pytest.fixture
    def ri(self, qapp, probe_color):
        w = ComplexRIWidget("z", probe_color)
        w.resize(600, 400)
        w.show()
        qapp.processEvents()
        return w

    def test_short_array_passthrough(self, ri):
        data = np.array([1+2j, 3+4j, 5+6j])
        ri.update_data(data)
        pd = ri.get_plot_data()
        # 2 series: Real, Imag
        assert len(pd) == 2
        assert pd[0]['name'] == 'Real'
        np.testing.assert_allclose(pd[0]['y'], [1, 3, 5])
        np.testing.assert_allclose(pd[1]['y'], [2, 4, 6])

    def test_long_array_x_spans_full_range(self, ri):
        N = 16000
        data = np.exp(1j * np.linspace(0, 10 * np.pi, N))
        ri.update_data(data)
        pd = ri.get_plot_data()
        x_real = np.array(pd[0]['x'])
        assert x_real[-1] > 5000, f"x max = {x_real[-1]}, expected > 5000"

    def test_zoom_in_shows_raw_data(self, ri, qapp):
        N = 16000
        data = np.exp(1j * np.linspace(0, 10 * np.pi, N))
        ri.update_data(data)
        pd = _zoom_and_extract(ri, qapp, 7000, 8000)
        y_real = np.array(pd[0]['y'])
        assert len(y_real) >= 900, f"Expected ~1000 raw points, got {len(y_real)}"
        assert len(y_real) <= 1100, f"Expected ~1000 raw points, got {len(y_real)}"

    def test_zoom_out_redownsamples(self, ri, qapp):
        N = 16000
        data = np.exp(1j * np.linspace(0, 10 * np.pi, N))
        ri.update_data(data)
        _zoom_and_extract(ri, qapp, 7000, 8000)
        pd = _zoom_and_extract(ri, qapp, 0, N)
        y = np.array(pd[0]['y'])
        assert len(y) <= 5000


# ── ComplexMAWidget ──────────────────────────────────────────

class TestComplexMAXAxis:
    """Mag & Phase downsampling preserves x-axis."""

    @pytest.fixture
    def ma(self, qapp, probe_color):
        w = ComplexMAWidget("z", probe_color)
        w.resize(600, 400)
        w.show()
        qapp.processEvents()
        return w

    def test_long_array_x_spans_full_range(self, ma):
        N = 16000
        data = np.exp(1j * np.linspace(0, 10 * np.pi, N))
        ma.update_data(data)
        pd = ma.get_plot_data()
        x_mag = np.array(pd[0]['x'])
        assert x_mag[-1] > 5000

    def test_zoom_in_shows_raw_data(self, ma, qapp):
        N = 16000
        data = np.exp(1j * np.linspace(0, 10 * np.pi, N))
        ma.update_data(data)
        pd = _zoom_and_extract(ma, qapp, 7000, 8000)
        y_mag = np.array(pd[0]['y'])
        assert len(y_mag) >= 900
        assert len(y_mag) <= 1100


# ── SingleCurveWidget ────────────────────────────────────────

class TestSingleCurveXAxis:
    """SingleCurveWidget (Log Mag, Lin Mag, Phase) downsampling."""

    @pytest.fixture
    def single(self, qapp, probe_color):
        w = SingleCurveWidget("z", probe_color, "Test")
        w.resize(600, 400)
        w.show()
        qapp.processEvents()
        return w

    def test_long_array_x_spans_full_range(self, single):
        N = 16000
        data = np.sin(np.linspace(0, 10 * np.pi, N))
        single.set_data(data, f"[{N}]")
        pd = single.get_plot_data()
        x = np.array(pd[0]['x'])
        assert x[-1] > 5000

    def test_zoom_in_shows_raw_data(self, single, qapp):
        N = 16000
        data = np.sin(np.linspace(0, 10 * np.pi, N))
        single.set_data(data, f"[{N}]")
        pd = _zoom_and_extract(single, qapp, 7000, 8000)
        y = np.array(pd[0]['y'])
        assert len(y) >= 900
        assert len(y) <= 1100

    def test_zoom_in_data_matches_original(self, single, qapp):
        N = 16000
        data = np.sin(np.linspace(0, 10 * np.pi, N))
        single.set_data(data, f"[{N}]")
        pd = _zoom_and_extract(single, qapp, 7000, 8000)
        x = np.array(pd[0]['x'])
        y = np.array(pd[0]['y'])
        # Verify raw data matches original
        i_min = int(x[0])
        i_max = int(x[-1]) + 1
        np.testing.assert_allclose(y, data[i_min:i_max], atol=1e-10)
