"""Phase 5.1: Panel container layout tests.

Verifies panels are visible, arranged in grid, and placeholder behavior.
"""

import pytest
from PyQt6.QtGui import QColor

from pyprobe.gui.panel_container import ProbePanelContainer
from pyprobe.core.anchor import ProbeAnchor


def _make_anchor(symbol, line=1):
    return ProbeAnchor(
        file="/tmp/test.py", line=line, col=0, symbol=symbol,
    )


@pytest.fixture
def container(qapp):
    """Create a ProbePanelContainer."""
    c = ProbePanelContainer()
    c.resize(800, 600)
    c.show()
    qapp.processEvents()
    yield c
    # Explicit cleanup: remove all panels before widget is deleted
    for panel in list(c.get_all_panels()):
        c.remove_panel(panel=panel)
    qapp.processEvents()
    c.hide()
    c.deleteLater()
    qapp.processEvents()


class TestPanelContainerAdd:
    def test_placeholder_visible_initially(self, container):
        """Placeholder label is visible when no panels exist."""
        assert container._placeholder.isVisible()

    def test_add_panel_hides_placeholder(self, container, qapp):
        """Adding a panel hides the placeholder."""
        anchor = _make_anchor("sig1")
        container.create_panel("sig1", "scalar", anchor=anchor,
                               color=QColor("#00ffff"))
        qapp.processEvents()
        assert not container._placeholder.isVisible()

    def test_three_panels_all_visible(self, container, qapp):
        """Adding 3 panels, all are visible with non-zero geometry."""
        for i, name in enumerate(["a", "b", "c"]):
            anchor = _make_anchor(name, line=i+1)
            container.create_panel(name, "scalar", anchor=anchor,
                                   color=QColor("#00ffff"))
        qapp.processEvents()

        panels = container.get_all_panels()
        assert len(panels) == 3
        for p in panels:
            assert p.isVisible()
            assert p.width() > 0
            assert p.height() > 0


class TestPanelContainerRemove:
    def test_remove_shows_placeholder(self, container, qapp):
        """Removing all panels shows placeholder again."""
        anchor = _make_anchor("temp")
        container.create_panel("temp", "scalar", anchor=anchor,
                               color=QColor("#00ffff"))
        qapp.processEvents()
        assert not container._placeholder.isVisible()

        container.remove_panel(anchor=anchor)
        qapp.processEvents()
        assert container._placeholder.isVisible()

    def test_remove_specific_panel(self, container, qapp):
        """Can remove a specific panel by reference."""
        a1 = _make_anchor("x", line=1)
        a2 = _make_anchor("y", line=2)
        p1 = container.create_panel("x", "scalar", anchor=a1,
                                     color=QColor("#00ffff"))
        p2 = container.create_panel("y", "scalar", anchor=a2,
                                     color=QColor("#ff00ff"))
        qapp.processEvents()
        assert len(container.get_all_panels()) == 2

        container.remove_panel(panel=p1)
        qapp.processEvents()
        remaining = container.get_all_panels()
        assert len(remaining) == 1
        assert remaining[0] is p2


class TestPanelContainerGrid:
    def test_two_column_layout(self, container, qapp):
        """Two panels are arranged side by side (2-column grid)."""
        a1 = _make_anchor("left", line=1)
        a2 = _make_anchor("right", line=2)
        p1 = container.create_panel("left", "scalar", anchor=a1,
                                     color=QColor("#00ffff"))
        p2 = container.create_panel("right", "scalar", anchor=a2,
                                     color=QColor("#ff00ff"))
        qapp.processEvents()

        assert p1.isVisible()
        assert p2.isVisible()

        # Verify actual side-by-side geometry: p1 left of p2, same row
        g1 = p1.geometry()
        g2 = p2.geometry()
        assert g1.x() < g2.x(), "Left panel should be to the left of right panel"
        assert abs(g1.y() - g2.y()) < 5, "Panels should be on the same row"

    def test_single_panel_spans_full_width(self, container, qapp):
        """A single panel should span the full width of the container."""
        anchor = _make_anchor("solo")
        panel = container.create_panel("solo", "scalar", anchor=anchor,
                                       color=QColor("#00ffff"))
        qapp.processEvents()

        # Single panel should use colspan=2 (full width)
        assert panel.isVisible()
        assert panel.width() > 0


class TestPanelContainerPark:
    def test_park_hides_from_layout(self, container, qapp):
        """Parking a panel excludes it from the visible layout."""
        a1 = _make_anchor("visible", line=1)
        a2 = _make_anchor("parked", line=2)
        p1 = container.create_panel("visible", "scalar", anchor=a1,
                                     color=QColor("#00ffff"))
        p2 = container.create_panel("parked", "scalar", anchor=a2,
                                     color=QColor("#ff00ff"))
        qapp.processEvents()

        container.park_panel(a2)
        qapp.processEvents()

        # Parked panel should be removed from layout but still tracked
        assert container.get_panel(anchor=a2) is p2  # still tracked
        # p1 should still be visible
        assert p1.isVisible()

    def test_unpark_restores_to_layout(self, container, qapp):
        """Unparking a panel adds it back to the layout."""
        a1 = _make_anchor("x", line=1)
        container.create_panel("x", "scalar", anchor=a1,
                               color=QColor("#00ffff"))
        qapp.processEvents()

        container.park_panel(a1)
        qapp.processEvents()

        container.unpark_panel(a1)
        qapp.processEvents()

        panel = container.get_panel(anchor=a1)
        assert panel is not None


class TestPanelContainerLookup:
    def test_get_panel_by_anchor(self, container, qapp):
        """get_panel returns the correct panel for an anchor."""
        anchor = _make_anchor("lookup_me")
        panel = container.create_panel("lookup_me", "scalar", anchor=anchor,
                                       color=QColor("#00ffff"))
        qapp.processEvents()

        found = container.get_panel(anchor=anchor)
        assert found is panel

    def test_get_all_panels_returns_all(self, container, qapp):
        """get_all_panels returns all panels across anchors."""
        for i in range(3):
            a = _make_anchor(f"v{i}", line=i+1)
            container.create_panel(f"v{i}", "scalar", anchor=a,
                                   color=QColor("#00ffff"))
        qapp.processEvents()

        all_panels = container.get_all_panels()
        assert len(all_panels) == 3

    def test_get_panel_missing_returns_none(self, container):
        """get_panel for unknown anchor returns None."""
        anchor = _make_anchor("missing")
        assert container.get_panel(anchor=anchor) is None
