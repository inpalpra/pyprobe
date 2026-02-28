"""M5: Reproduce reset zoom bug — instant snap vs. animated zoom-out.

Creates a WaveformWidget with 16k data points, zooms in programmatically,
calls reset(), and checks whether the view range snaps to full extent
after a single processEvents() — or drifts over time (animation).
"""

import time
import numpy as np
import pytest
from PyQt6.QtGui import QColor

from pyprobe.plugins.builtins.waveform import WaveformWidget
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D


@pytest.fixture
def waveform(qtbot, qapp, probe_color):
    w = WaveformWidget("test_signal", probe_color)
    qtbot.addWidget(w)
    w.resize(600, 400)
    w.show()
    qapp.processEvents()
    yield w
    w.close()
    w.deleteLater()
    qapp.processEvents()


class TestResetZoomBehavior:
    """Verify reset() snaps to full range instantly (no animation)."""

    def _get_view_range(self, waveform):
        vb = waveform._plot_widget.getPlotItem().getViewBox()
        return vb.viewRange()

    def test_reset_snaps_to_full_range_instantly(self, waveform, qapp):
        """After zoom + reset, view range must match full data
        after a single processEvents() — not animated over frames."""
        N = 16000
        data = np.sin(np.linspace(0, 10 * np.pi, N))
        waveform.update_data(data, DTYPE_ARRAY_1D)
        qapp.processEvents()

        # 1. Record the natural full-view range
        full_x_range, full_y_range = self._get_view_range(waveform)

        # 2. Programmatically zoom into a narrow window
        plot_item = waveform._plot_widget.getPlotItem()
        plot_item.setXRange(5000, 6000, padding=0)
        qapp.processEvents()

        # Confirm zoom took effect
        zoomed_x, _ = self._get_view_range(waveform)
        assert zoomed_x[0] > 1000, f"Zoom didn't take: x_min={zoomed_x[0]}"

        # Pin axes (simulates user having zoomed)
        ac = waveform.axis_controller
        assert ac is not None
        ac.set_pinned('x', True)
        ac.set_pinned('y', True)

        # 3. Call reset
        ac.reset()
        qapp.processEvents()

        # 4. Check: range should be at or near full extent IMMEDIATELY
        post_x, post_y = self._get_view_range(waveform)

        # The x-range should span close to [0, N-1]
        # Allow tolerance for pyqtgraph padding
        assert post_x[0] < 500, (
            f"Reset didn't snap X min: expected <500, got {post_x[0]}"
        )
        assert post_x[1] > N - 1500, (
            f"Reset didn't snap X max: expected >{N-1500}, got {post_x[1]}"
        )

    def test_reset_view_range_does_not_drift(self, waveform, qapp):
        """After reset, pumping more events should NOT change the range
        (no ongoing animation)."""
        N = 16000
        data = np.sin(np.linspace(0, 10 * np.pi, N))
        waveform.update_data(data, DTYPE_ARRAY_1D)
        qapp.processEvents()

        # Zoom in
        plot_item = waveform._plot_widget.getPlotItem()
        plot_item.setXRange(5000, 6000, padding=0)
        qapp.processEvents()

        ac = waveform.axis_controller
        ac.set_pinned('x', True)
        ac.set_pinned('y', True)

        # Reset
        ac.reset()
        qapp.processEvents()
        range_t0 = self._get_view_range(waveform)

        # Pump 200ms more of events
        deadline = time.monotonic() + 0.2
        while time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.01)

        range_t1 = self._get_view_range(waveform)

        # Ranges should be unchanged (no drift/animation)
        np.testing.assert_allclose(
            range_t0[0], range_t1[0], atol=1.0,
            err_msg="X range drifted after reset — animation detected"
        )
