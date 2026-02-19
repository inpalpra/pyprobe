"""Comprehensive E2E GUI tests for Draw Mode (LINE / DOTS / BOTH).

Tests cover the full rendering pipeline: create widget → feed data →
set draw mode → verify curve properties → switch mode → verify again.

Widget types tested:
  - WaveformWidget (1D real, 2D multi-row)
  - ComplexRIWidget (Real & Imag)
  - ComplexMAWidget (Log Mag & Phase)
  - SingleCurveWidget via plugins: LogMag, LinearMag, PhaseRad, PhaseDeg

Constellation is exempt (scatter-only, no line drawing).
"""

import numpy as np
import pytest
import pyqtgraph as pg
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

from pyprobe.plots.draw_mode import DrawMode, apply_draw_mode
from pyprobe.plugins.builtins.waveform import WaveformWidget, WaveformPlugin
from pyprobe.plugins.builtins.complex_plots import (
    ComplexRIWidget, ComplexRIPlugin,
    ComplexMAWidget, ComplexMAPlugin,
    SingleCurveWidget,
    LogMagPlugin, LinearMagPlugin, PhaseRadPlugin, PhaseDegPlugin,
)
from pyprobe.core.data_classifier import (
    DTYPE_ARRAY_1D, DTYPE_ARRAY_2D, DTYPE_ARRAY_COMPLEX,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_pen(curve) -> bool:
    """True if curve has a visible pen (not NoPen style)."""
    pen = curve.opts.get('pen')
    if pen is None:
        return False
    if hasattr(pen, 'style'):
        return pen.style() != Qt.PenStyle.NoPen
    return True


def _has_symbol(curve) -> bool:
    """True if curve has a non-None symbol."""
    return curve.opts.get('symbol') is not None


def _assert_mode(curve, mode: DrawMode):
    """Assert a curve's pen/symbol state matches the expected DrawMode."""
    if mode == DrawMode.LINE:
        assert _has_pen(curve), "LINE mode should have a visible pen"
        assert not _has_symbol(curve), "LINE mode should have no symbol"
    elif mode == DrawMode.DOTS:
        assert not _has_pen(curve), "DOTS mode should have no visible pen"
        assert _has_symbol(curve), "DOTS mode should have a symbol"
        assert curve.opts['symbol'] == 's', "Symbol should be filled square"
    elif mode == DrawMode.BOTH:
        assert _has_pen(curve), "BOTH mode should have a visible pen"
        assert _has_symbol(curve), "BOTH mode should have a symbol"
        assert curve.opts['symbol'] == 's', "Symbol should be filled square"


# Every possible (from, to) transition
ALL_TRANSITIONS = [
    (DrawMode.LINE, DrawMode.DOTS),
    (DrawMode.LINE, DrawMode.BOTH),
    (DrawMode.DOTS, DrawMode.LINE),
    (DrawMode.DOTS, DrawMode.BOTH),
    (DrawMode.BOTH, DrawMode.LINE),
    (DrawMode.BOTH, DrawMode.DOTS),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def probe_color():
    return QColor("#00ffff")


@pytest.fixture
def complex_data():
    """Return a 128-sample complex sinusoid for testing."""
    t = np.linspace(0, 2 * np.pi, 128)
    return np.exp(1j * t).astype(np.complex128)


@pytest.fixture
def real_data():
    """Return a 100-sample real sinusoid for testing."""
    return np.sin(np.linspace(0, 4 * np.pi, 100))


# ---------------------------------------------------------------------------
# 1. WaveformWidget — real 1D data
# ---------------------------------------------------------------------------

class TestWaveformE2E:
    """E2E draw mode tests for WaveformWidget with real 1D data."""

    @pytest.fixture
    def widget(self, qapp, probe_color, real_data):
        w = WaveformWidget("signal", probe_color)
        w.resize(600, 400)
        w.show()
        qapp.processEvents()
        w.update_data(real_data, DTYPE_ARRAY_1D)
        qapp.processEvents()
        yield w
        w.hide()
        w.deleteLater()
        qapp.processEvents()

    def test_initial_line(self, widget):
        """Widget starts in LINE mode with data on curve."""
        _assert_mode(widget._curves[0], DrawMode.LINE)
        _, y = widget._curves[0].getData()
        assert y is not None and len(y) > 0

    def test_set_dots(self, widget):
        """Switch to DOTS — curve shows squares, no line."""
        widget.set_draw_mode(0, DrawMode.DOTS)
        _assert_mode(widget._curves[0], DrawMode.DOTS)

    def test_set_both(self, widget):
        """Switch to BOTH — curve shows line AND squares."""
        widget.set_draw_mode(0, DrawMode.BOTH)
        _assert_mode(widget._curves[0], DrawMode.BOTH)

    @pytest.mark.parametrize("from_mode,to_mode", ALL_TRANSITIONS,
                             ids=[f"{a.name}->{b.name}" for a, b in ALL_TRANSITIONS])
    def test_transitions(self, widget, from_mode, to_mode):
        """Every (from→to) mode transition works."""
        widget.set_draw_mode(0, from_mode)
        _assert_mode(widget._curves[0], from_mode)
        widget.set_draw_mode(0, to_mode)
        _assert_mode(widget._curves[0], to_mode)

    def test_data_update_preserves_mode(self, widget, real_data):
        """Feeding new data does not reset draw mode."""
        widget.set_draw_mode(0, DrawMode.DOTS)
        widget.update_data(real_data * 2, DTYPE_ARRAY_1D)
        _assert_mode(widget._curves[0], DrawMode.DOTS)
        assert widget.get_draw_mode(0) == DrawMode.DOTS

    def test_data_correct_after_mode_change(self, widget, real_data):
        """Y-data is still correct after switching to DOTS."""
        widget.set_draw_mode(0, DrawMode.DOTS)
        _, y = widget._curves[0].getData()
        np.testing.assert_allclose(y, real_data, rtol=1e-6)


# ---------------------------------------------------------------------------
# 2. WaveformWidget — 2D multi-row data
# ---------------------------------------------------------------------------

class TestWaveform2DE2E:
    """E2E draw mode tests for WaveformWidget with 2D multi-row data."""

    @pytest.fixture
    def widget(self, qapp, probe_color):
        w = WaveformWidget("multi", probe_color)
        w.resize(600, 400)
        w.show()
        data = np.array([
            np.sin(np.linspace(0, 2*np.pi, 50)),
            np.cos(np.linspace(0, 2*np.pi, 50)),
        ])
        w.update_data(data, DTYPE_ARRAY_2D, shape=data.shape)
        qapp.processEvents()
        yield w
        w.hide()
        w.deleteLater()
        qapp.processEvents()

    def test_two_curves_exist(self, widget):
        assert len(widget._curves) == 2

    def test_independent_modes(self, widget):
        """Row 0 can be DOTS while row 1 stays LINE."""
        widget.set_draw_mode(0, DrawMode.DOTS)
        _assert_mode(widget._curves[0], DrawMode.DOTS)
        _assert_mode(widget._curves[1], DrawMode.LINE)

    def test_all_modes_per_row(self, widget):
        """Assign LINE/DOTS/BOTH to different rows at once."""
        widget.set_draw_mode(0, DrawMode.BOTH)
        widget.set_draw_mode(1, DrawMode.DOTS)
        _assert_mode(widget._curves[0], DrawMode.BOTH)
        _assert_mode(widget._curves[1], DrawMode.DOTS)

    @pytest.mark.parametrize("from_mode,to_mode", ALL_TRANSITIONS,
                             ids=[f"{a.name}->{b.name}" for a, b in ALL_TRANSITIONS])
    def test_row_transitions(self, widget, from_mode, to_mode):
        """Every transition on row 0, row 1 stays LINE."""
        widget.set_draw_mode(0, from_mode)
        widget.set_draw_mode(0, to_mode)
        _assert_mode(widget._curves[0], to_mode)
        _assert_mode(widget._curves[1], DrawMode.LINE)  # unaffected


# ---------------------------------------------------------------------------
# 3. ComplexRIWidget — Real & Imaginary
# ---------------------------------------------------------------------------

class TestComplexRIE2E:
    """E2E draw mode tests for ComplexRIWidget."""

    @pytest.fixture
    def widget(self, qapp, probe_color, complex_data):
        w = ComplexRIWidget("z", probe_color)
        w.resize(600, 400)
        w.show()
        w.update_data(complex_data)
        qapp.processEvents()
        yield w
        w.hide()
        w.deleteLater()
        qapp.processEvents()

    def test_initial_line(self, widget):
        _assert_mode(widget._real_curve, DrawMode.LINE)
        _assert_mode(widget._imag_curve, DrawMode.LINE)

    def test_real_dots_imag_line(self, widget):
        """Real as DOTS, Imag stays LINE."""
        widget.set_draw_mode('Real', DrawMode.DOTS)
        _assert_mode(widget._real_curve, DrawMode.DOTS)
        _assert_mode(widget._imag_curve, DrawMode.LINE)

    def test_real_line_imag_both(self, widget):
        """Real as LINE, Imag as BOTH."""
        widget.set_draw_mode('Imag', DrawMode.BOTH)
        _assert_mode(widget._real_curve, DrawMode.LINE)
        _assert_mode(widget._imag_curve, DrawMode.BOTH)

    def test_both_series_dots(self, widget):
        """Both series in DOTS mode."""
        widget.set_draw_mode('Real', DrawMode.DOTS)
        widget.set_draw_mode('Imag', DrawMode.DOTS)
        _assert_mode(widget._real_curve, DrawMode.DOTS)
        _assert_mode(widget._imag_curve, DrawMode.DOTS)

    @pytest.mark.parametrize("series", ['Real', 'Imag'])
    @pytest.mark.parametrize("from_mode,to_mode", ALL_TRANSITIONS,
                             ids=[f"{a.name}->{b.name}" for a, b in ALL_TRANSITIONS])
    def test_all_transitions(self, widget, series, from_mode, to_mode):
        """Every transition on each series."""
        curve = widget._real_curve if series == 'Real' else widget._imag_curve
        widget.set_draw_mode(series, from_mode)
        _assert_mode(curve, from_mode)
        widget.set_draw_mode(series, to_mode)
        _assert_mode(curve, to_mode)

    def test_data_update_preserves_mode(self, widget, complex_data):
        """New data does not reset draw mode."""
        widget.set_draw_mode('Real', DrawMode.DOTS)
        widget.set_draw_mode('Imag', DrawMode.BOTH)
        widget.update_data(complex_data * 2)
        _assert_mode(widget._real_curve, DrawMode.DOTS)
        _assert_mode(widget._imag_curve, DrawMode.BOTH)

    def test_data_correct_after_mode_change(self, widget, complex_data):
        """Y-data is still correct after switching to DOTS."""
        widget.set_draw_mode('Real', DrawMode.DOTS)
        _, y = widget._real_curve.getData()
        np.testing.assert_allclose(y, complex_data.real, rtol=1e-6)


# ---------------------------------------------------------------------------
# 4. ComplexMAWidget — Magnitude & Phase (dual axis)
# ---------------------------------------------------------------------------

class TestComplexMAE2E:
    """E2E draw mode tests for ComplexMAWidget."""

    @pytest.fixture
    def widget(self, qapp, probe_color, complex_data):
        w = ComplexMAWidget("z", probe_color)
        w.resize(600, 400)
        w.show()
        w.update_data(complex_data)
        qapp.processEvents()
        yield w
        w.hide()
        w.deleteLater()
        qapp.processEvents()

    def test_initial_line(self, widget):
        _assert_mode(widget._mag_curve, DrawMode.LINE)
        _assert_mode(widget._phase_curve, DrawMode.LINE)

    def test_mag_dots_phase_line(self, widget):
        widget.set_draw_mode('Log Mag', DrawMode.DOTS)
        _assert_mode(widget._mag_curve, DrawMode.DOTS)
        _assert_mode(widget._phase_curve, DrawMode.LINE)

    def test_mag_line_phase_both(self, widget):
        widget.set_draw_mode('Phase', DrawMode.BOTH)
        _assert_mode(widget._mag_curve, DrawMode.LINE)
        _assert_mode(widget._phase_curve, DrawMode.BOTH)

    @pytest.mark.parametrize("series", ['Log Mag', 'Phase'])
    @pytest.mark.parametrize("from_mode,to_mode", ALL_TRANSITIONS,
                             ids=[f"{a.name}->{b.name}" for a, b in ALL_TRANSITIONS])
    def test_all_transitions(self, widget, series, from_mode, to_mode):
        curve = widget._mag_curve if series == 'Log Mag' else widget._phase_curve
        widget.set_draw_mode(series, from_mode)
        _assert_mode(curve, from_mode)
        widget.set_draw_mode(series, to_mode)
        _assert_mode(curve, to_mode)

    def test_phase_curve_is_plotdataitem(self, widget):
        """Phase curve must be PlotDataItem for symbol support."""
        assert isinstance(widget._phase_curve, pg.PlotDataItem)


# ---------------------------------------------------------------------------
# 5. Plugin-level E2E — LogMag, LinearMag, PhaseRad, PhaseDeg
# ---------------------------------------------------------------------------

class _SingleCurvePluginMixin:
    """Shared tests for single-curve complex plugins via the plugin layer."""

    PLUGIN_CLASS = None
    SERIES_KEY = None

    @pytest.fixture
    def plugin(self):
        return self.PLUGIN_CLASS()

    @pytest.fixture
    def widget(self, qapp, probe_color, plugin, complex_data):
        w = plugin.create_widget("z", probe_color)
        w.resize(600, 400)
        w.show()
        plugin.update(w, complex_data, DTYPE_ARRAY_COMPLEX)
        qapp.processEvents()
        yield w
        w.hide()
        w.deleteLater()
        qapp.processEvents()

    def test_is_single_curve(self, widget):
        assert isinstance(widget, SingleCurveWidget)
        assert len(widget.series_keys) == 1
        assert widget.series_keys[0] == self.SERIES_KEY

    def test_initial_line(self, widget):
        _assert_mode(widget._curve, DrawMode.LINE)

    def test_set_dots(self, widget):
        widget.set_draw_mode(self.SERIES_KEY, DrawMode.DOTS)
        _assert_mode(widget._curve, DrawMode.DOTS)

    def test_set_both(self, widget):
        widget.set_draw_mode(self.SERIES_KEY, DrawMode.BOTH)
        _assert_mode(widget._curve, DrawMode.BOTH)

    @pytest.mark.parametrize("from_mode,to_mode", ALL_TRANSITIONS,
                             ids=[f"{a.name}->{b.name}" for a, b in ALL_TRANSITIONS])
    def test_transitions(self, widget, from_mode, to_mode):
        widget.set_draw_mode(self.SERIES_KEY, from_mode)
        _assert_mode(widget._curve, from_mode)
        widget.set_draw_mode(self.SERIES_KEY, to_mode)
        _assert_mode(widget._curve, to_mode)

    def test_data_update_preserves_mode(self, widget, plugin, complex_data):
        widget.set_draw_mode(self.SERIES_KEY, DrawMode.BOTH)
        plugin.update(widget, complex_data * 2, DTYPE_ARRAY_COMPLEX)
        _assert_mode(widget._curve, DrawMode.BOTH)

    def test_data_on_curve(self, widget):
        """Curve should have real data plotted."""
        _, y = widget._curve.getData()
        assert y is not None and len(y) > 0


class TestLogMagE2E(_SingleCurvePluginMixin):
    PLUGIN_CLASS = LogMagPlugin
    SERIES_KEY = "Magnitude (dB)"


class TestLinearMagE2E(_SingleCurvePluginMixin):
    PLUGIN_CLASS = LinearMagPlugin
    SERIES_KEY = "Magnitude"


class TestPhaseRadE2E(_SingleCurvePluginMixin):
    PLUGIN_CLASS = PhaseRadPlugin
    SERIES_KEY = "Phase (rad)"


class TestPhaseDegE2E(_SingleCurvePluginMixin):
    PLUGIN_CLASS = PhaseDegPlugin
    SERIES_KEY = "Phase (deg)"


# ---------------------------------------------------------------------------
# 6. WaveformPlugin full pipeline (plugin create → update → mode → verify)
# ---------------------------------------------------------------------------

class TestWaveformPluginE2E:
    """E2E through the WaveformPlugin layer."""

    @pytest.fixture
    def plugin(self):
        return WaveformPlugin()

    @pytest.fixture
    def widget(self, qapp, probe_color, plugin, real_data):
        w = plugin.create_widget("sig", probe_color)
        w.resize(600, 400)
        w.show()
        plugin.update(w, real_data, DTYPE_ARRAY_1D)
        qapp.processEvents()
        yield w
        w.hide()
        w.deleteLater()
        qapp.processEvents()

    def test_initial_line(self, widget):
        _assert_mode(widget._curves[0], DrawMode.LINE)

    @pytest.mark.parametrize("mode", list(DrawMode))
    def test_each_mode(self, widget, mode):
        widget.set_draw_mode(0, mode)
        _assert_mode(widget._curves[0], mode)

    def test_round_trip(self, widget):
        """LINE → DOTS → BOTH → LINE full cycle."""
        for mode in [DrawMode.LINE, DrawMode.DOTS, DrawMode.BOTH, DrawMode.LINE]:
            widget.set_draw_mode(0, mode)
            _assert_mode(widget._curves[0], mode)
            assert widget.get_draw_mode(0) == mode

    def test_plugin_update_after_mode_change(self, widget, plugin, real_data):
        """Plugin.update() after mode change keeps mode intact."""
        widget.set_draw_mode(0, DrawMode.DOTS)
        plugin.update(widget, real_data * 3, DTYPE_ARRAY_1D)
        _assert_mode(widget._curves[0], DrawMode.DOTS)
        _, y = widget._curves[0].getData()
        np.testing.assert_allclose(y, real_data * 3, rtol=1e-6)


# ---------------------------------------------------------------------------
# 7. ComplexRIPlugin full pipeline
# ---------------------------------------------------------------------------

class TestComplexRIPluginE2E:
    """E2E through the ComplexRIPlugin layer."""

    @pytest.fixture
    def plugin(self):
        return ComplexRIPlugin()

    @pytest.fixture
    def widget(self, qapp, probe_color, plugin, complex_data):
        w = plugin.create_widget("iq", probe_color)
        w.resize(600, 400)
        w.show()
        plugin.update(w, complex_data, DTYPE_ARRAY_COMPLEX)
        qapp.processEvents()
        yield w
        w.hide()
        w.deleteLater()
        qapp.processEvents()

    def test_initial_line(self, widget):
        _assert_mode(widget._real_curve, DrawMode.LINE)
        _assert_mode(widget._imag_curve, DrawMode.LINE)

    def test_mixed_modes(self, widget):
        """Real: BOTH, Imag: DOTS simultaneously."""
        widget.set_draw_mode('Real', DrawMode.BOTH)
        widget.set_draw_mode('Imag', DrawMode.DOTS)
        _assert_mode(widget._real_curve, DrawMode.BOTH)
        _assert_mode(widget._imag_curve, DrawMode.DOTS)

    def test_plugin_update_preserves(self, widget, plugin, complex_data):
        widget.set_draw_mode('Real', DrawMode.DOTS)
        plugin.update(widget, complex_data * 0.5, DTYPE_ARRAY_COMPLEX)
        _assert_mode(widget._real_curve, DrawMode.DOTS)


# ---------------------------------------------------------------------------
# 8. ComplexMAPlugin full pipeline
# ---------------------------------------------------------------------------

class TestComplexMAPluginE2E:
    """E2E through the ComplexMAPlugin layer."""

    @pytest.fixture
    def plugin(self):
        return ComplexMAPlugin()

    @pytest.fixture
    def widget(self, qapp, probe_color, plugin, complex_data):
        w = plugin.create_widget("iq", probe_color)
        w.resize(600, 400)
        w.show()
        plugin.update(w, complex_data, DTYPE_ARRAY_COMPLEX)
        qapp.processEvents()
        yield w
        w.hide()
        w.deleteLater()
        qapp.processEvents()

    def test_initial_line(self, widget):
        _assert_mode(widget._mag_curve, DrawMode.LINE)
        _assert_mode(widget._phase_curve, DrawMode.LINE)

    def test_mixed_modes(self, widget):
        widget.set_draw_mode('Log Mag', DrawMode.DOTS)
        widget.set_draw_mode('Phase', DrawMode.BOTH)
        _assert_mode(widget._mag_curve, DrawMode.DOTS)
        _assert_mode(widget._phase_curve, DrawMode.BOTH)

    def test_plugin_update_preserves(self, widget, plugin, complex_data):
        widget.set_draw_mode('Phase', DrawMode.DOTS)
        plugin.update(widget, complex_data * 2, DTYPE_ARRAY_COMPLEX)
        _assert_mode(widget._phase_curve, DrawMode.DOTS)
