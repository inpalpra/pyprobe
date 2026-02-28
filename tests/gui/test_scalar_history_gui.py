"""Phase 2.3: Scalar history chart visual correctness tests.

Verifies curve data, value label, clear_history, and stats.
"""

import numpy as np
import pytest
from PyQt6.QtGui import QColor

from pyprobe.plugins.builtins.scalar_history import ScalarHistoryWidget, ScalarHistoryPlugin
from pyprobe.core.data_classifier import DTYPE_SCALAR


@pytest.fixture
def scalar_history(qtbot, qapp, probe_color):
    """Create a ScalarHistoryWidget for testing."""
    w = ScalarHistoryWidget("counter", probe_color)
    qtbot.addWidget(w)
    w.resize(400, 300)
    w.show()
    qapp.processEvents()
    yield w
    w.close()
    w.deleteLater()
    qapp.processEvents()


class TestScalarHistoryData:
    def test_sequential_scalars(self, scalar_history):
        """Sequential scalar values appear as history curve."""
        for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
            scalar_history.update_data(v, DTYPE_SCALAR)

        _, y = scalar_history._curve.getData()
        np.testing.assert_allclose(y, [1, 2, 3, 4, 5])

    def test_value_label_shows_latest(self, scalar_history):
        """Value label displays the most recent scalar."""
        scalar_history.update_data(42.0, DTYPE_SCALAR)
        assert "42" in scalar_history._value_label.text()

        scalar_history.update_data(99.5, DTYPE_SCALAR)
        assert "99.5" in scalar_history._value_label.text()

    def test_history_buffer_fifo(self, scalar_history):
        """History deque respects maxlen."""
        maxlen = scalar_history.DEFAULT_HISTORY_LENGTH
        for i in range(maxlen + 100):
            scalar_history.update_data(float(i), DTYPE_SCALAR)

        assert len(scalar_history._history) == maxlen
        # Most recent value should be the last one
        assert scalar_history._history[-1] == float(maxlen + 99)

    def test_complex_scalar_uses_magnitude(self, scalar_history):
        """Complex scalar is stored as absolute value."""
        scalar_history.update_data(3+4j, DTYPE_SCALAR)
        assert scalar_history._history[-1] == pytest.approx(5.0)

    def test_none_is_ignored(self, scalar_history):
        """Passing None does not crash or append."""
        initial_len = len(scalar_history._history)
        scalar_history.update_data(None, DTYPE_SCALAR)
        assert len(scalar_history._history) == initial_len


class TestScalarHistoryClear:
    def test_clear_empties_curve(self, scalar_history, qapp):
        """clear_history() empties the curve data."""
        for v in [1, 2, 3]:
            scalar_history.update_data(float(v), DTYPE_SCALAR)

        scalar_history.clear_history()
        qapp.processEvents()

        _, y = scalar_history._curve.getData()
        assert y is None or len(y) == 0

    def test_clear_resets_labels(self, scalar_history):
        """clear_history() resets value and stats labels."""
        scalar_history.update_data(42.0, DTYPE_SCALAR)
        scalar_history.clear_history()

        assert scalar_history._value_label.text() == "--"
        assert "--" in scalar_history._stats_label.text()


class TestScalarHistoryUpdateHistory:
    def test_replace_history(self, scalar_history):
        """update_history() replaces the buffer entirely."""
        scalar_history.update_data(1.0, DTYPE_SCALAR)
        scalar_history.update_history([10.0, 20.0, 30.0])

        _, y = scalar_history._curve.getData()
        np.testing.assert_allclose(y, [10, 20, 30])
        assert "30" in scalar_history._value_label.text()


class TestScalarHistoryStats:
    def test_stats_after_values(self, scalar_history):
        """Stats label shows correct min/max/mean."""
        for v in [2.0, 4.0, 6.0]:
            scalar_history.update_data(v, DTYPE_SCALAR)

        text = scalar_history._stats_label.text()
        assert "Min: 2" in text
        assert "Max: 6" in text
        assert "Mean: 4" in text


class TestScalarHistoryPlugin:
    def test_can_handle_scalar(self):
        assert ScalarHistoryPlugin().can_handle(DTYPE_SCALAR, None)

    def test_cannot_handle_array(self):
        assert not ScalarHistoryPlugin().can_handle('array_1d', None)

    def test_create_widget(self, qtbot, qapp, probe_color):
        w = ScalarHistoryPlugin().create_widget("x", probe_color)
        qtbot.addWidget(w)
        assert isinstance(w, ScalarHistoryWidget)
        w.close()
        w.deleteLater()
        qapp.processEvents()
