"""Shared test fixtures for PyProbe test suite.

Provides centralized QApplication, sample data factories, and
PlotAssertions helper for verifying rendered widget state.
"""

import sys
import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.capture_record import CaptureRecord


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication — shared by all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def sample_anchor():
    """A reusable ProbeAnchor for testing."""
    return ProbeAnchor(
        file="/tmp/test_script.py",
        line=10,
        col=4,
        symbol="signal_x",
        func="process",
        is_assignment=True,
    )


@pytest.fixture
def sample_anchor_factory():
    """Factory fixture — create ProbeAnchors with custom fields."""
    def _make(symbol="test_var", line=10, col=0, file="/tmp/test.py",
              func="", is_assignment=False):
        return ProbeAnchor(
            file=file, line=line, col=col,
            symbol=symbol, func=func, is_assignment=is_assignment,
        )
    return _make


@pytest.fixture
def sample_record_factory(sample_anchor_factory):
    """Factory fixture — create CaptureRecords with defaults."""
    _seq = [0]

    def _make(value=42.0, dtype="scalar", shape=None, symbol="test_var",
              anchor=None, seq_num=None, timestamp=0, logical_order=0):
        if anchor is None:
            anchor = sample_anchor_factory(symbol=symbol)
        if seq_num is None:
            _seq[0] += 1
            seq_num = _seq[0]
        return CaptureRecord(
            anchor=anchor,
            value=value,
            dtype=dtype,
            shape=shape,
            seq_num=seq_num,
            timestamp=timestamp,
            logical_order=logical_order,
        )
    return _make


@pytest.fixture
def probe_color():
    """Default probe color for tests."""
    return QColor("#00ffff")


class PlotAssertions:
    """Helper methods to inspect actual pyqtgraph widget state.

    Usage in tests::

        pa = PlotAssertions()
        pa.assert_curve_data(waveform_widget, expected_y=[1, 2, 3])
    """

    @staticmethod
    def assert_curve_data(widget, expected_y, curve_index=0, approx=True):
        """Assert that curve data matches expected y values.

        Works with WaveformWidget (has ``_curves`` list).
        """
        assert hasattr(widget, '_curves'), "Widget has no _curves attribute"
        assert curve_index < len(widget._curves), (
            f"Curve index {curve_index} out of range (have {len(widget._curves)})"
        )
        x_data, y_data = widget._curves[curve_index].getData()
        assert y_data is not None, "Curve y_data is None"
        if approx:
            np.testing.assert_allclose(y_data, expected_y, rtol=1e-6)
        else:
            np.testing.assert_array_equal(y_data, expected_y)

    @staticmethod
    def assert_scatter_data(widget, expected_real, expected_imag,
                            scatter_index=-1):
        """Assert scatter plot contains expected I/Q data.

        Works with ConstellationWidget (has ``_scatter_items`` list).
        ``scatter_index=-1`` checks the brightest (newest) scatter item.
        """
        assert hasattr(widget, '_scatter_items'), "Widget has no _scatter_items"
        scatter = widget._scatter_items[scatter_index]
        points = scatter.data
        assert len(points) > 0, "Scatter has no data points"
        actual_x = np.array([p[0] for p in points])
        actual_y = np.array([p[1] for p in points])
        np.testing.assert_allclose(actual_x, expected_real, rtol=1e-6)
        np.testing.assert_allclose(actual_y, expected_imag, rtol=1e-6)

    @staticmethod
    def assert_axis_range(widget, axis, expected_min, expected_max, tol=0.5):
        """Assert that a plot axis range approximately matches expectations."""
        assert hasattr(widget, '_plot_widget'), "Widget has no _plot_widget"
        view_box = widget._plot_widget.getPlotItem().getViewBox()
        ranges = view_box.viewRange()
        idx = 0 if axis == 'x' else 1
        actual_min, actual_max = ranges[idx]
        assert abs(actual_min - expected_min) < tol, (
            f"{axis} min: expected ~{expected_min}, got {actual_min}"
        )
        assert abs(actual_max - expected_max) < tol, (
            f"{axis} max: expected ~{expected_max}, got {actual_max}"
        )

    @staticmethod
    def assert_curve_count(widget, n):
        """Assert widget has exactly n curves."""
        assert hasattr(widget, '_curves'), "Widget has no _curves attribute"
        assert len(widget._curves) == n, (
            f"Expected {n} curves, got {len(widget._curves)}"
        )

    @staticmethod
    def assert_widget_visible(widget):
        """Assert that a widget is visible."""
        assert widget.isVisible(), f"Widget {widget} is not visible"

    @staticmethod
    def assert_label_text(label, expected_text, contains=True):
        """Assert label text matches (or contains) expected string."""
        actual = label.text()
        if contains:
            assert expected_text in actual, (
                f"Expected label to contain '{expected_text}', got '{actual}'"
            )
        else:
            assert actual == expected_text, (
                f"Expected label text '{expected_text}', got '{actual}'"
            )


@pytest.fixture
def plot_assertions():
    """PlotAssertions helper instance."""
    return PlotAssertions()
