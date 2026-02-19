"""Phase 5.2: Scalar watch sidebar tests.

Verifies adding scalars, updating values, and remove behavior.
"""

import pytest
from PyQt6.QtGui import QColor

from pyprobe.gui.scalar_watch_window import ScalarWatchSidebar
from pyprobe.core.anchor import ProbeAnchor


def _make_anchor(symbol="counter", line=10):
    return ProbeAnchor(
        file="/tmp/test.py", line=line, col=0, symbol=symbol,
    )


@pytest.fixture
def sidebar(qapp):
    """Create a ScalarWatchSidebar."""
    s = ScalarWatchSidebar()
    s.resize(250, 400)
    s.show()
    qapp.processEvents()
    return s


class TestScalarWatchAdd:
    def test_add_scalar_creates_card(self, sidebar, qapp):
        """Adding a scalar creates a card widget."""
        anchor = _make_anchor()
        sidebar.add_scalar(anchor, QColor("#00ffff"))
        qapp.processEvents()

        assert sidebar.has_scalar(anchor)

    def test_add_scalar_hides_placeholder(self, sidebar, qapp):
        """Adding a scalar hides the placeholder."""
        anchor = _make_anchor()
        sidebar.add_scalar(anchor, QColor("#00ffff"))
        qapp.processEvents()

        assert not sidebar._placeholder.isVisible()

    def test_duplicate_add_ignored(self, sidebar, qapp):
        """Adding the same anchor twice doesn't duplicate."""
        anchor = _make_anchor()
        sidebar.add_scalar(anchor, QColor("#00ffff"))
        sidebar.add_scalar(anchor, QColor("#00ffff"))
        qapp.processEvents()

        assert len(sidebar.get_watched_anchors()) == 1


class TestScalarWatchUpdate:
    def test_update_changes_value_label(self, sidebar, qapp):
        """Updating a scalar changes the displayed value."""
        anchor = _make_anchor()
        sidebar.add_scalar(anchor, QColor("#00ffff"))
        sidebar.update_scalar(anchor, 42.0)
        qapp.processEvents()

        _, value_label = sidebar._scalars[anchor]
        assert "42" in value_label.text()

    def test_update_float_formatting(self, sidebar, qapp):
        """Float values are formatted correctly."""
        anchor = _make_anchor()
        sidebar.add_scalar(anchor, QColor("#00ffff"))
        sidebar.update_scalar(anchor, 3.14159)
        qapp.processEvents()

        _, value_label = sidebar._scalars[anchor]
        assert "3.14" in value_label.text()

    def test_update_complex_formatting(self, sidebar, qapp):
        """Complex values are formatted with real+imag notation."""
        anchor = _make_anchor()
        sidebar.add_scalar(anchor, QColor("#00ffff"))
        sidebar.update_scalar(anchor, 1.5 + 2.3j)
        qapp.processEvents()

        _, value_label = sidebar._scalars[anchor]
        text = value_label.text()
        assert "1.5" in text or "1.50" in text
        assert "2.3" in text or "2.30" in text

    def test_update_scientific_notation(self, sidebar, qapp):
        """Very small float uses scientific notation."""
        anchor = _make_anchor()
        sidebar.add_scalar(anchor, QColor("#00ffff"))
        sidebar.update_scalar(anchor, 0.00012345)
        qapp.processEvents()

        _, value_label = sidebar._scalars[anchor]
        assert "e" in value_label.text().lower()

    def test_update_unknown_anchor_no_error(self, sidebar, qapp):
        """Updating an unknown anchor does not raise."""
        sidebar.update_scalar(_make_anchor("missing"), 99.0)
        qapp.processEvents()  # should not crash


class TestScalarWatchRemove:
    def test_remove_scalar(self, sidebar, qapp):
        """Removing a scalar removes its card."""
        anchor = _make_anchor()
        sidebar.add_scalar(anchor, QColor("#00ffff"))
        qapp.processEvents()
        assert sidebar.has_scalar(anchor)

        sidebar.remove_scalar(anchor)
        qapp.processEvents()
        assert not sidebar.has_scalar(anchor)

    def test_remove_shows_placeholder(self, sidebar, qapp):
        """Removing all scalars shows placeholder again."""
        anchor = _make_anchor()
        sidebar.add_scalar(anchor, QColor("#00ffff"))
        sidebar.remove_scalar(anchor)
        qapp.processEvents()

        assert sidebar._placeholder.isVisible()

    def test_remove_emits_signal(self, sidebar, qapp):
        """Removing scalar emits scalar_removed signal."""
        anchor = _make_anchor()
        sidebar.add_scalar(anchor, QColor("#00ffff"))

        received = []
        sidebar.scalar_removed.connect(lambda a: received.append(a))
        sidebar._remove_scalar(anchor)
        qapp.processEvents()

        assert len(received) == 1
        assert received[0] == anchor


class TestScalarWatchMultiple:
    def test_multiple_scalars_tracked(self, sidebar, qapp):
        """Multiple scalars can be added and all are tracked."""
        anchors = [_make_anchor(f"s{i}", line=i) for i in range(3)]
        for a in anchors:
            sidebar.add_scalar(a, QColor("#00ffff"))
        qapp.processEvents()

        watched = sidebar.get_watched_anchors()
        assert len(watched) == 3
        for a in anchors:
            assert sidebar.has_scalar(a)

    def test_remove_one_of_multiple(self, sidebar, qapp):
        """Removing one scalar keeps the others."""
        a1 = _make_anchor("keep", line=1)
        a2 = _make_anchor("remove", line=2)
        sidebar.add_scalar(a1, QColor("#00ffff"))
        sidebar.add_scalar(a2, QColor("#ff00ff"))
        qapp.processEvents()

        sidebar.remove_scalar(a2)
        qapp.processEvents()

        assert sidebar.has_scalar(a1)
        assert not sidebar.has_scalar(a2)
        assert not sidebar._placeholder.isVisible()

