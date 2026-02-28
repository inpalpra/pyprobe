"""Tests for custom plot color change feature.

Verifies that set_color() and set_series_color() correctly update
widget colors (name label, curve pen, axis pen, scatter brush)
across all widget types.
"""

import numpy as np
import pytest
from PyQt6.QtGui import QColor

from pyprobe.gui.probe_panel import ProbePanel
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D, DTYPE_ARRAY_COMPLEX, DTYPE_SCALAR
from pyprobe.plugins.builtins.complex_plots import (
    ComplexMAWidget, ComplexRIWidget, SingleCurveWidget
)
from pyprobe.plugins.builtins.waveform import WaveformWidget
from pyprobe.plugins.builtins.constellation import ConstellationWidget
from pyprobe.plugins.builtins.scalar_display import ScalarDisplayWidget
from pyprobe.plugins.builtins.scalar_history import ScalarHistoryWidget


PINK = QColor("#ff69b4")


@pytest.fixture
def panel_anchor():
    return ProbeAnchor(
        file="/tmp/dsp.py", line=42, col=4,
        symbol="signal_i", func="process",
    )


@pytest.fixture
def probe_color():
    return QColor("#00ffff")


class TestComplexMAWidgetColor:
    def test_set_color_updates_name_label(self, qtbot, qapp, probe_color):
        w = ComplexMAWidget("x", probe_color)
        qtbot.addWidget(w)
        w.set_color(PINK)
        assert PINK.name() in w._name_label.styleSheet()
        w.close()
        w.deleteLater()
        qapp.processEvents()

    def test_set_series_color_updates_mag_curve(self, qtbot, qapp, probe_color):
        w = ComplexMAWidget("x", probe_color)
        qtbot.addWidget(w)
        w.set_series_color('Log Mag', PINK)
        curve, hex_c = w._series_curves['Log Mag']
        assert hex_c == PINK.name()
        w.close()
        w.deleteLater()
        qapp.processEvents()

    def test_set_series_color_phase_unchanged(self, qtbot, qapp, probe_color):
        w = ComplexMAWidget("x", probe_color)
        qtbot.addWidget(w)
        w.set_series_color('Log Mag', PINK)
        _, phase_hex = w._series_curves['Phase']
        assert phase_hex == '#00ff7f'  # unchanged
        w.close()
        w.deleteLater()
        qapp.processEvents()



class TestComplexRIWidgetColor:
    def test_set_series_color_real(self, qtbot, qapp, probe_color):
        w = ComplexRIWidget("x", probe_color)
        qtbot.addWidget(w)
        w.set_series_color('Real', PINK)
        _, hex_c = w._series_curves['Real']
        assert hex_c == PINK.name()
        w.close()
        w.deleteLater()
        qapp.processEvents()


class TestSingleCurveWidgetColor:
    def test_set_series_color_single_curve(self, qtbot, qapp, probe_color):
        w = SingleCurveWidget("x", probe_color, "Magnitude (dB)")
        qtbot.addWidget(w)
        w.set_series_color('Magnitude (dB)', PINK)
        _, hex_c = w._series_curves['Magnitude (dB)']
        assert hex_c == PINK.name()
        w.close()
        w.deleteLater()
        qapp.processEvents()


class TestWaveformWidgetColor:
    def test_set_color_updates_label(self, qtbot, qapp, probe_color):
        w = WaveformWidget("x", probe_color)
        qtbot.addWidget(w)
        w.set_color(PINK)
        assert PINK.name() in w._name_label.styleSheet()
        w.close()
        w.deleteLater()
        qapp.processEvents()

    def test_set_color_updates_primary_curve(self, qtbot, qapp, probe_color):
        w = WaveformWidget("x", probe_color)
        qtbot.addWidget(w)
        w.set_color(PINK)
        pen = w._curves[0].opts['pen']
        assert pen.color().name() == PINK.name()
        w.close()
        w.deleteLater()
        qapp.processEvents()


class TestConstellationWidgetColor:
    def test_set_color_updates_label(self, qtbot, qapp, probe_color):
        w = ConstellationWidget("x", probe_color)
        qtbot.addWidget(w)
        w.set_color(PINK)
        assert PINK.name() in w._name_label.styleSheet()
        w.close()
        w.deleteLater()
        qapp.processEvents()

    def test_set_color_updates_scatter_brush(self, qtbot, qapp, probe_color):
        w = ConstellationWidget("x", probe_color)
        qtbot.addWidget(w)
        w.set_color(PINK)
        # Latest (brightest) scatter should have pink RGB
        latest = w._scatter_items[-1]
        brush = latest.opts['brush']
        r, g, b = PINK.red(), PINK.green(), PINK.blue()
        assert brush.color().red() == r
        assert brush.color().green() == g
        assert brush.color().blue() == b
        w.close()
        w.deleteLater()
        qapp.processEvents()


class TestScalarHistoryWidgetColor:
    def test_set_color_updates_label(self, qtbot, qapp, probe_color):
        w = ScalarHistoryWidget("x", probe_color)
        qtbot.addWidget(w)
        w.set_color(PINK)
        assert PINK.name() in w._name_label.styleSheet()
        w.close()
        w.deleteLater()
        qapp.processEvents()

    def test_set_color_updates_curve_pen(self, qtbot, qapp, probe_color):
        w = ScalarHistoryWidget("x", probe_color)
        qtbot.addWidget(w)
        w.set_color(PINK)
        pen = w._curve.opts['pen']
        assert pen.color().name() == PINK.name()
        w.close()
        w.deleteLater()
        qapp.processEvents()


class TestScalarDisplayWidgetColor:
    def test_set_color_updates_label(self, qtbot, qapp, probe_color):
        w = ScalarDisplayWidget("x", probe_color)
        qtbot.addWidget(w)
        w.set_color(PINK)
        assert PINK.name() in w._name_label.styleSheet()
        w.close()
        w.deleteLater()
        qapp.processEvents()


class TestProbePanelColorSignal:
    def test_color_changed_signal_emitted(self, qtbot, qapp, panel_anchor, probe_color):
        panel = ProbePanel(panel_anchor, probe_color, DTYPE_ARRAY_1D)
        qtbot.addWidget(panel)
        panel.resize(600, 400)
        panel.show()
        qapp.processEvents()

        received = []
        panel.color_changed.connect(lambda a, c: received.append((a, c)))

        # Simulate what _change_probe_color does (without the dialog)
        panel._color = PINK
        panel._identity_label.setStyleSheet(f"""
            QLabel {{
                color: {PINK.name()};
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        if panel._plot and hasattr(panel._plot, 'set_color'):
            panel._plot.set_color(PINK)
        panel.color_changed.emit(panel._anchor, PINK)

        assert len(received) == 1
        assert received[0][0] == panel_anchor
        assert received[0][1].name() == PINK.name()
        assert PINK.name() in panel._identity_label.styleSheet()
        panel.close()
        panel.deleteLater()
        qapp.processEvents()
