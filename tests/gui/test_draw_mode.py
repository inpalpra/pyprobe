"""Tests for per-series draw mode (LINE / DOTS / BOTH) on line-plot widgets.

Verifies that draw mode can be set per series, persists across data updates,
and that independent per-series modes work correctly in multi-curve widgets.
"""

import numpy as np
import pytest
import pyqtgraph as pg
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

from pyprobe.plots.draw_mode import DrawMode, apply_draw_mode
from pyprobe.plugins.builtins.waveform import WaveformWidget
from pyprobe.plugins.builtins.complex_plots import (
    ComplexRIWidget, ComplexMAWidget, SingleCurveWidget,
)
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D, DTYPE_ARRAY_2D


def _has_pen(curve) -> bool:
    """Check if a curve has a visible pen (not NoPen)."""
    pen = curve.opts.get('pen')
    if pen is None:
        return False
    if hasattr(pen, 'style'):
        return pen.style() != Qt.PenStyle.NoPen
    return True


@pytest.fixture
def probe_color():
    return QColor("#00ffff")


# === apply_draw_mode helper ===

class TestApplyDrawMode:
    def test_line_mode(self, qapp):
        """LINE mode sets pen and no symbol."""
        pw = pg.PlotWidget()
        curve = pw.plot()
        apply_draw_mode(curve, DrawMode.LINE, '#00ffff')
        assert _has_pen(curve)
        assert curve.opts.get('symbol') is None

    def test_dots_mode(self, qapp):
        """DOTS mode sets symbol='s' and no pen."""
        pw = pg.PlotWidget()
        curve = pw.plot()
        apply_draw_mode(curve, DrawMode.DOTS, '#ff00ff')
        assert not _has_pen(curve)
        assert curve.opts.get('symbol') == 's'
        assert curve.opts.get('symbolSize') == 5

    def test_both_mode(self, qapp):
        """BOTH mode sets both pen and symbol."""
        pw = pg.PlotWidget()
        curve = pw.plot()
        apply_draw_mode(curve, DrawMode.BOTH, '#ffff00')
        assert _has_pen(curve)
        assert curve.opts.get('symbol') == 's'
        assert curve.opts.get('symbolSize') == 4


# === WaveformWidget ===

class TestWaveformDrawMode:
    @pytest.fixture
    def waveform(self, qapp, probe_color):
        w = WaveformWidget("test_signal", probe_color)
        w.resize(600, 400)
        w.show()
        qapp.processEvents()
        return w

    def test_default_draw_mode_is_line(self, waveform):
        """Initial draw mode is LINE."""
        assert waveform.get_draw_mode(0) == DrawMode.LINE

    def test_set_draw_mode_dots(self, waveform):
        """Setting DOTS mode removes pen and adds symbol."""
        data = np.array([1.0, 2.0, 3.0])
        waveform.update_data(data, DTYPE_ARRAY_1D)
        waveform.set_draw_mode(0, DrawMode.DOTS)
        assert waveform.get_draw_mode(0) == DrawMode.DOTS
        assert not _has_pen(waveform._curves[0])
        assert waveform._curves[0].opts.get('symbol') == 's'

    def test_set_draw_mode_both(self, waveform):
        """Setting BOTH mode has pen and symbol."""
        waveform.update_data(np.arange(5, dtype=float), DTYPE_ARRAY_1D)
        waveform.set_draw_mode(0, DrawMode.BOTH)
        assert _has_pen(waveform._curves[0])
        assert waveform._curves[0].opts.get('symbol') == 's'

    def test_set_draw_mode_back_to_line(self, waveform):
        """Cycling LINE→DOTS→LINE removes symbols."""
        waveform.update_data(np.arange(5, dtype=float), DTYPE_ARRAY_1D)
        waveform.set_draw_mode(0, DrawMode.DOTS)
        waveform.set_draw_mode(0, DrawMode.LINE)
        assert waveform._curves[0].opts.get('symbol') is None

    def test_draw_mode_survives_data_update(self, waveform):
        """Draw mode persists across data updates."""
        waveform.update_data(np.arange(5, dtype=float), DTYPE_ARRAY_1D)
        waveform.set_draw_mode(0, DrawMode.DOTS)
        # Update with new data
        waveform.update_data(np.arange(10, dtype=float), DTYPE_ARRAY_1D)
        assert waveform.get_draw_mode(0) == DrawMode.DOTS
        # Verify the mode was re-applied
        assert waveform._curves[0].opts.get('symbol') == 's'

    def test_per_series_independence_2d(self, waveform):
        """2D waveform rows can have independent draw modes."""
        data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=float)
        waveform.update_data(data, DTYPE_ARRAY_2D, shape=data.shape)
        assert len(waveform._curves) == 3

        waveform.set_draw_mode(0, DrawMode.DOTS)
        waveform.set_draw_mode(1, DrawMode.BOTH)
        waveform.set_draw_mode(2, DrawMode.LINE)

        # Row 0: dots only
        assert not _has_pen(waveform._curves[0])
        assert waveform._curves[0].opts.get('symbol') == 's'

        # Row 1: both
        assert _has_pen(waveform._curves[1])
        assert waveform._curves[1].opts.get('symbol') == 's'

        # Row 2: line only
        assert waveform._curves[2].opts.get('symbol') is None

    def test_series_keys(self, waveform):
        assert waveform.series_keys == [0]
        data = np.array([[1, 2], [3, 4]], dtype=float)
        waveform.update_data(data, DTYPE_ARRAY_2D, shape=data.shape)
        assert waveform.series_keys == [0, 1]


# === ComplexRIWidget ===

class TestComplexRIDrawMode:
    @pytest.fixture
    def ri_widget(self, qapp, probe_color):
        w = ComplexRIWidget("z", probe_color)
        w.resize(600, 400)
        w.show()
        qapp.processEvents()
        return w

    def test_series_keys(self, ri_widget):
        assert ri_widget.series_keys == ['Real', 'Imag']

    def test_default_mode(self, ri_widget):
        assert ri_widget.get_draw_mode('Real') == DrawMode.LINE
        assert ri_widget.get_draw_mode('Imag') == DrawMode.LINE

    def test_per_series_independence(self, ri_widget):
        """Real and Imag can have different draw modes."""
        ri_widget.set_draw_mode('Real', DrawMode.DOTS)
        ri_widget.set_draw_mode('Imag', DrawMode.LINE)

        # Real: dots
        assert not _has_pen(ri_widget._real_curve)
        assert ri_widget._real_curve.opts.get('symbol') == 's'

        # Imag: line
        assert ri_widget._imag_curve.opts.get('symbol') is None
        assert _has_pen(ri_widget._imag_curve)


# === ComplexMAWidget ===

class TestComplexMADrawMode:
    @pytest.fixture
    def ma_widget(self, qapp, probe_color):
        w = ComplexMAWidget("z", probe_color)
        w.resize(600, 400)
        w.show()
        qapp.processEvents()
        return w

    def test_series_keys(self, ma_widget):
        assert ma_widget.series_keys == ['Log Mag', 'Phase']

    def test_phase_curve_is_plotdataitem(self, ma_widget):
        """Phase curve must be PlotDataItem (not PlotCurveItem) for symbol support."""
        assert isinstance(ma_widget._phase_curve, pg.PlotDataItem)

    def test_set_draw_mode(self, ma_widget):
        ma_widget.set_draw_mode('Phase', DrawMode.BOTH)
        assert ma_widget._phase_curve.opts.get('symbol') == 's'


# === SingleCurveWidget ===

class TestSingleCurveDrawMode:
    @pytest.fixture
    def single_widget(self, qapp, probe_color):
        w = SingleCurveWidget("z", probe_color, "Log Mag (dB)")
        w.resize(600, 400)
        w.show()
        qapp.processEvents()
        return w

    def test_series_keys(self, single_widget):
        assert single_widget.series_keys == ['Log Mag (dB)']

    def test_set_draw_mode(self, single_widget):
        single_widget.set_draw_mode('Log Mag (dB)', DrawMode.DOTS)
        assert single_widget._curve.opts.get('symbol') == 's'
        assert not _has_pen(single_widget._curve)
