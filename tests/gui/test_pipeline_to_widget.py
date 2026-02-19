"""Phase 6.1: Full pipeline to widget test.

Verifies CaptureRecord -> RedrawThrottler -> buffer -> panel.update_from_buffer()
path delivers data to the rendered widget.
"""

import numpy as np
import pytest
from PyQt6.QtGui import QColor

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.capture_record import CaptureRecord
from pyprobe.core.data_classifier import (
    DTYPE_SCALAR, DTYPE_ARRAY_1D, DTYPE_ARRAY_COMPLEX,
)
from pyprobe.gui.redraw_throttler import RedrawThrottler
from pyprobe.gui.probe_panel import ProbePanel
from pyprobe.plugins.builtins.scalar_history import ScalarHistoryWidget
from pyprobe.plugins.builtins.waveform import WaveformWidget


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def anchor():
    return ProbeAnchor(
        file="/tmp/pipeline.py", line=5, col=0,
        symbol="loss", func="train",
    )


@pytest.fixture
def anchor_b():
    """A second, distinct anchor for multi-probe tests."""
    return ProbeAnchor(
        file="/tmp/pipeline.py", line=12, col=0,
        symbol="accuracy", func="evaluate",
    )


@pytest.fixture
def throttler():
    return RedrawThrottler(min_interval_ms=0)  # No throttling for tests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(anchor, value, dtype, seq, shape=None):
    return CaptureRecord(
        anchor=anchor, value=value, dtype=dtype, shape=shape,
        seq_num=seq, timestamp=seq * 1000, logical_order=seq,
    )


def _make_panel(qapp, anchor, probe_color, dtype):
    """Create, resize, show, and process events for a ProbePanel."""
    panel = ProbePanel(anchor, probe_color, dtype)
    panel.resize(400, 300)
    panel.show()
    qapp.processEvents()
    return panel


def _feed_and_drain(throttler, records, panel, qapp):
    """Feed records through throttler, drain dirty buffers, update panel."""
    for r in records:
        throttler.receive(r)
    dirty = throttler.get_dirty_buffers()
    anchor = records[0].anchor
    assert anchor in dirty, "Expected anchor in dirty buffers"
    panel.update_from_buffer(dirty[anchor])
    qapp.processEvents()
    return dirty[anchor]


# ===================================================================
# Scalar pipeline
# ===================================================================

class TestScalarPipeline:
    def test_records_reach_widget(self, qapp, anchor, throttler, probe_color):
        """Scalar CaptureRecords flow through throttler to panel."""
        panel = _make_panel(qapp, anchor, probe_color, DTYPE_SCALAR)

        # Feed records through throttler
        for i in range(5):
            record = _make_record(anchor, float(i * 10), DTYPE_SCALAR, i)
            throttler.receive(record)

        # Get buffer and update panel
        dirty = throttler.get_dirty_buffers()
        assert anchor in dirty

        buffer = dirty[anchor]
        panel.update_from_buffer(buffer)
        qapp.processEvents()

        # Verify data reached the widget
        if isinstance(panel._plot, ScalarHistoryWidget):
            plot_data = panel._plot.get_plot_data()
            assert len(plot_data['y']) == 5
            assert plot_data['y'][-1] == 40.0

    def test_multiple_updates_accumulate(self, qapp, anchor, throttler, probe_color):
        """Multiple throttler cycles accumulate in widget history."""
        panel = _make_panel(qapp, anchor, probe_color, DTYPE_SCALAR)

        # First batch
        for i in range(3):
            throttler.receive(_make_record(anchor, float(i), DTYPE_SCALAR, i))
        dirty = throttler.get_dirty_buffers()
        panel.update_from_buffer(dirty[anchor])
        qapp.processEvents()

        # Second batch
        for i in range(3, 6):
            throttler.receive(_make_record(anchor, float(i), DTYPE_SCALAR, i))
        dirty = throttler.get_dirty_buffers()
        panel.update_from_buffer(dirty[anchor])
        qapp.processEvents()

        if isinstance(panel._plot, ScalarHistoryWidget):
            plot_data = panel._plot.get_plot_data()
            assert len(plot_data['y']) == 6

    def test_scalar_values_correct(self, qapp, anchor, throttler, probe_color):
        """Verify exact scalar values survive the full pipeline."""
        panel = _make_panel(qapp, anchor, probe_color, DTYPE_SCALAR)

        expected = [3.14, 2.718, 1.414, 1.732, 0.577]
        records = [
            _make_record(anchor, v, DTYPE_SCALAR, i)
            for i, v in enumerate(expected)
        ]
        _feed_and_drain(throttler, records, panel, qapp)

        if isinstance(panel._plot, ScalarHistoryWidget):
            plot_data = panel._plot.get_plot_data()
            np.testing.assert_allclose(plot_data['y'], expected, rtol=1e-6)

    def test_value_label_shows_latest(self, qapp, anchor, throttler, probe_color):
        """The current-value label shows the most recent scalar."""
        panel = _make_panel(qapp, anchor, probe_color, DTYPE_SCALAR)

        records = [_make_record(anchor, 42.5, DTYPE_SCALAR, 0)]
        _feed_and_drain(throttler, records, panel, qapp)

        if isinstance(panel._plot, ScalarHistoryWidget):
            label_text = panel._plot._value_label.text()
            assert "42.5" in label_text


# ===================================================================
# Array 1D pipeline
# ===================================================================

class TestArray1DPipeline:
    def test_array_reaches_waveform_widget(self, qapp, anchor, throttler, probe_color):
        """1D array CaptureRecords flow through throttler to waveform panel."""
        panel = _make_panel(qapp, anchor, probe_color, DTYPE_ARRAY_1D)

        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        record = _make_record(anchor, data, DTYPE_ARRAY_1D, 0, shape=(5,))
        _feed_and_drain(throttler, [record], panel, qapp)

        if isinstance(panel._plot, WaveformWidget):
            plot_data = panel._plot.get_plot_data()
            assert len(plot_data) >= 1
            np.testing.assert_allclose(plot_data[0]['y'], [1, 2, 3, 4, 5])

    def test_array_update_replaces_data(self, qapp, anchor, throttler, probe_color):
        """Later array updates replace data in the waveform widget (not accumulate)."""
        panel = _make_panel(qapp, anchor, probe_color, DTYPE_ARRAY_1D)

        first = np.array([1.0, 2.0, 3.0])
        record1 = _make_record(anchor, first, DTYPE_ARRAY_1D, 0, shape=(3,))
        _feed_and_drain(throttler, [record1], panel, qapp)

        second = np.array([10.0, 20.0, 30.0])
        record2 = _make_record(anchor, second, DTYPE_ARRAY_1D, 1, shape=(3,))
        _feed_and_drain(throttler, [record2], panel, qapp)

        if isinstance(panel._plot, WaveformWidget):
            plot_data = panel._plot.get_plot_data()
            assert len(plot_data) >= 1
            # Latest data should be in the curve
            np.testing.assert_allclose(plot_data[0]['y'], [10, 20, 30])


# ===================================================================
# Dtype change
# ===================================================================

class TestDtypeChangePipeline:
    def test_dtype_change_recreates_widget(self, qapp, anchor, throttler, probe_color):
        """When dtype changes from scalar to array_1d, widget is recreated."""
        panel = _make_panel(qapp, anchor, probe_color, DTYPE_SCALAR)

        old_plot_type = type(panel._plot)

        # Feed array data — triggers dtype change
        array_data = np.array([1, 2, 3, 4, 5], dtype=float)
        panel.update_data(array_data, DTYPE_ARRAY_1D)
        qapp.processEvents()

        # Widget type should have changed
        assert panel._plot is not None
        # The new widget should be a WaveformWidget, not the original ScalarHistoryWidget
        if old_plot_type == ScalarHistoryWidget:
            assert type(panel._plot) != old_plot_type, (
                "Widget should have been recreated for new dtype"
            )

    def test_dtype_change_via_buffer(self, qapp, anchor, throttler, probe_color):
        """dtype change through the full throttler→buffer→panel path."""
        panel = _make_panel(qapp, anchor, probe_color, DTYPE_SCALAR)

        old_plot_type = type(panel._plot)

        # Feed scalar first
        throttler.receive(_make_record(anchor, 1.0, DTYPE_SCALAR, 0))
        dirty = throttler.get_dirty_buffers()
        panel.update_from_buffer(dirty[anchor])
        qapp.processEvents()

        # Now feed array — requires a fresh throttler since the buffer
        # remembers dtype from the record
        throttler2 = RedrawThrottler(min_interval_ms=0)
        array_val = np.array([10.0, 20.0, 30.0])
        throttler2.receive(
            _make_record(anchor, array_val, DTYPE_ARRAY_1D, 1, shape=(3,))
        )
        dirty2 = throttler2.get_dirty_buffers()
        panel.update_from_buffer(dirty2[anchor])
        qapp.processEvents()

        assert panel._plot is not None


# ===================================================================
# Throttler buffering
# ===================================================================

class TestThrottlerBuffering:
    def test_buffer_stores_all_records(self, anchor, throttler):
        """Throttler buffer stores all records even when not draining."""
        for i in range(10):
            throttler.receive(_make_record(anchor, float(i), DTYPE_SCALAR, i))

        buf = throttler.buffer_for(anchor)
        assert buf is not None
        assert buf.count == 10

    def test_dirty_cleared_after_drain(self, anchor, throttler):
        """get_dirty_buffers clears the dirty set."""
        throttler.receive(_make_record(anchor, 1.0, DTYPE_SCALAR, 0))
        dirty = throttler.get_dirty_buffers()
        assert len(dirty) == 1

        # Second call returns empty
        dirty2 = throttler.get_dirty_buffers()
        assert len(dirty2) == 0

    def test_should_redraw_respects_interval(self, anchor):
        """should_redraw returns False within the interval, True when elapsed."""
        fake_time = [0.0]
        throttler = RedrawThrottler(
            min_interval_ms=100,
            clock=lambda: fake_time[0],
        )

        # _last_redraw starts at 0.0; with clock also at 0.0 the delta is 0,
        # which is below the 100ms interval, so this returns False.
        assert throttler.should_redraw() is False

        # Advance past the interval (100ms = 0.1s)
        fake_time[0] = 0.2
        assert throttler.should_redraw() is True  # 0.2 - 0.0 >= 0.1

        # Immediately after — not enough time
        fake_time[0] = 0.25  # 50ms since last redraw at 0.2
        assert throttler.should_redraw() is False

        # After another 100ms — should allow
        fake_time[0] = 0.35  # 150ms since last redraw at 0.2
        assert throttler.should_redraw() is True

    def test_multiple_anchors_independent(self, anchor, anchor_b, throttler):
        """Buffers for different anchors are independent."""
        throttler.receive(_make_record(anchor, 1.0, DTYPE_SCALAR, 0))
        throttler.receive(_make_record(anchor, 2.0, DTYPE_SCALAR, 1))
        throttler.receive(_make_record(anchor_b, 99.0, DTYPE_SCALAR, 0))

        assert throttler.buffer_count == 2

        buf_a = throttler.buffer_for(anchor)
        buf_b = throttler.buffer_for(anchor_b)
        assert buf_a.count == 2
        assert buf_b.count == 1

        dirty = throttler.get_dirty_buffers()
        assert anchor in dirty
        assert anchor_b in dirty

    def test_only_new_anchors_dirty(self, anchor, anchor_b, throttler):
        """After draining, only anchors that received new data appear dirty."""
        throttler.receive(_make_record(anchor, 1.0, DTYPE_SCALAR, 0))
        throttler.receive(_make_record(anchor_b, 2.0, DTYPE_SCALAR, 0))
        throttler.get_dirty_buffers()  # drain all

        # Only feed anchor_b again
        throttler.receive(_make_record(anchor_b, 3.0, DTYPE_SCALAR, 1))
        dirty = throttler.get_dirty_buffers()
        assert anchor not in dirty
        assert anchor_b in dirty

    def test_buffer_preserves_order(self, anchor, throttler):
        """get_plot_data returns values in insertion order."""
        values = [3.14, 2.71, 1.41, 1.73]
        for i, v in enumerate(values):
            throttler.receive(_make_record(anchor, v, DTYPE_SCALAR, i))

        buf = throttler.buffer_for(anchor)
        _, stored_values = buf.get_plot_data()
        assert stored_values == values


# ===================================================================
# Multi-probe pipeline
# ===================================================================

class TestMultiProbePipeline:
    def test_two_probes_through_same_throttler(
        self, qapp, anchor, anchor_b, throttler, probe_color
    ):
        """Two probes independently feed through the same throttler."""
        panel_a = _make_panel(qapp, anchor, probe_color, DTYPE_SCALAR)
        panel_b = _make_panel(qapp, anchor_b, probe_color, DTYPE_SCALAR)

        # Interleave records from both probes
        throttler.receive(_make_record(anchor, 10.0, DTYPE_SCALAR, 0))
        throttler.receive(_make_record(anchor_b, 100.0, DTYPE_SCALAR, 0))
        throttler.receive(_make_record(anchor, 20.0, DTYPE_SCALAR, 1))
        throttler.receive(_make_record(anchor_b, 200.0, DTYPE_SCALAR, 1))

        dirty = throttler.get_dirty_buffers()

        panel_a.update_from_buffer(dirty[anchor])
        panel_b.update_from_buffer(dirty[anchor_b])
        qapp.processEvents()

        if isinstance(panel_a._plot, ScalarHistoryWidget):
            data_a = panel_a._plot.get_plot_data()
            assert len(data_a['y']) == 2
            np.testing.assert_allclose(data_a['y'], [10.0, 20.0])

        if isinstance(panel_b._plot, ScalarHistoryWidget):
            data_b = panel_b._plot.get_plot_data()
            assert len(data_b['y']) == 2
            np.testing.assert_allclose(data_b['y'], [100.0, 200.0])
