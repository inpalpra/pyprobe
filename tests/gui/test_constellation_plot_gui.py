"""Phase 2.2: Constellation plot visual correctness tests.

Verifies scatter plot data, history fade, and stats for complex I/Q data.
"""

import numpy as np
import pytest
from PyQt6.QtGui import QColor

from pyprobe.plugins.builtins.constellation import ConstellationWidget, ConstellationPlugin
from pyprobe.core.data_classifier import DTYPE_ARRAY_COMPLEX


@pytest.fixture
def constellation(qtbot, qapp, probe_color):
    """Create a ConstellationWidget for testing."""
    w = ConstellationWidget("iq_signal", probe_color)
    qtbot.addWidget(w)
    w.resize(400, 400)
    w.show()
    qapp.processEvents()
    yield w
    w.close()
    w.deleteLater()
    qapp.processEvents()


class TestConstellationData:
    def test_complex_array_renders(self, constellation):
        """Complex array populates scatter items."""
        data = np.array([1+1j, -1+1j, -1-1j, 1-1j])
        constellation.update_data(data, DTYPE_ARRAY_COMPLEX)

        # Newest data goes to last scatter item (brightest)
        scatter = constellation._scatter_items[-1]
        points = scatter.data
        assert len(points) == 4

    def test_scatter_real_imag_values(self, constellation):
        """Scatter plot contains correct real/imag coordinates."""
        data = np.array([1+2j, 3+4j])
        constellation.update_data(data, DTYPE_ARRAY_COMPLEX)

        scatter = constellation._scatter_items[-1]
        points = scatter.data
        real_vals = np.array([p[0] for p in points])
        imag_vals = np.array([p[1] for p in points])
        np.testing.assert_allclose(real_vals, [1.0, 3.0])
        np.testing.assert_allclose(imag_vals, [2.0, 4.0])

    def test_real_array_treated_as_complex(self, constellation):
        """Real-only array is cast to complex (imag=0)."""
        data = np.array([1.0, 2.0, 3.0])
        constellation.update_data(data, DTYPE_ARRAY_COMPLEX)

        scatter = constellation._scatter_items[-1]
        points = scatter.data
        imag_vals = np.array([p[1] for p in points])
        np.testing.assert_allclose(imag_vals, [0.0, 0.0, 0.0])

    def test_none_is_ignored(self, constellation):
        """Passing None does not crash."""
        constellation.update_data(None, DTYPE_ARRAY_COMPLEX)


class TestConstellationHistory:
    def test_history_length_limited(self, constellation):
        """History does not exceed HISTORY_LENGTH."""
        for i in range(10):
            data = np.array([complex(i, i)])
            constellation.update_data(data, DTYPE_ARRAY_COMPLEX)

        assert len(constellation._history) == constellation.HISTORY_LENGTH

    def test_multiple_frames_populate_scatter(self, constellation):
        """Multiple frames put data into multiple scatter items."""
        for i in range(3):
            data = np.array([complex(i, -i)])
            constellation.update_data(data, DTYPE_ARRAY_COMPLEX)

        # 3 frames of data, scattered into last 3 scatter items
        # scatter_items[-1] = newest, scatter_items[-3] = oldest
        for idx in range(-3, 0):
            scatter = constellation._scatter_items[idx]
            assert len(scatter.data) == 1


class TestConstellationMarkers:
    def test_marker_drag_updates_stored_position(self, constellation, qapp):
        """Dragging a marker commits the new position to MarkerStore."""
        data = np.array([0 + 0j, 10 + 10j])
        constellation.update_data(data, DTYPE_ARRAY_COMPLEX)

        store = constellation._marker_store
        marker = store.add_marker("history_4", 0.0, 0.0)
        qapp.processEvents()

        assert marker.id in constellation._marker_glyphs
        glyph = constellation._marker_glyphs[marker.id]
        glyph.signaler.marker_moved.emit(marker.id, 9.5, 9.5)
        qapp.processEvents()

        updated = store.get_marker(marker.id)
        assert updated is not None
        assert updated.x == pytest.approx(10.0)
        assert updated.y == pytest.approx(10.0)

        # Simulate pressing Run again: marker should stay at dragged location.
        constellation.update_data(data, DTYPE_ARRAY_COMPLEX)
        qapp.processEvents()
        updated = store.get_marker(marker.id)
        assert updated is not None
        assert updated.x == pytest.approx(10.0)
        assert updated.y == pytest.approx(10.0)


class TestConstellationStats:
    def test_power_display(self, constellation):
        """Stats label shows power in dB and symbol count."""
        data = np.array([1+0j, 0+1j, -1+0j, 0-1j])
        constellation.update_data(data, DTYPE_ARRAY_COMPLEX)

        text = constellation._stats_label.text()
        assert "Power:" in text
        assert "dB" in text
        assert "Symbols: 4" in text

    def test_name_label(self, constellation):
        """Name label matches variable name."""
        assert constellation._name_label.text() == "iq_signal"


class TestConstellationPlugin:
    def test_can_handle_complex(self):
        plugin = ConstellationPlugin()
        assert plugin.can_handle(DTYPE_ARRAY_COMPLEX, None)

    def test_cannot_handle_scalar(self):
        plugin = ConstellationPlugin()
        assert not plugin.can_handle('scalar', None)

    def test_create_widget(self, qtbot, qapp, probe_color):
        plugin = ConstellationPlugin()
        w = plugin.create_widget("z", probe_color)
        qtbot.addWidget(w)
        assert isinstance(w, ConstellationWidget)
        w.close()
        w.deleteLater()
        qapp.processEvents()
