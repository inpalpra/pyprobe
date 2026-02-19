"""Phase 5.3: Color manager tests.

Verifies deterministic color assignment, LRU emphasis, and color cycling.
"""

import pytest
from PyQt6.QtGui import QColor

from pyprobe.gui.color_manager import ColorManager
from pyprobe.core.anchor import ProbeAnchor


def _anchor(symbol, line=1):
    return ProbeAnchor(
        file="/tmp/test.py", line=line, col=0, symbol=symbol,
    )


@pytest.fixture
def cm(qapp):
    """Fresh ColorManager."""
    return ColorManager()


class TestColorAssignment:
    def test_first_assignment_returns_color(self, cm):
        """First call returns a QColor."""
        color = cm.get_color(_anchor("x"))
        assert isinstance(color, QColor)

    def test_same_anchor_same_color(self, cm):
        """Same anchor always returns same color."""
        a = _anchor("x")
        c1 = cm.get_color(a)
        c2 = cm.get_color(a)
        assert c1.name() == c2.name()

    def test_different_anchors_different_colors(self, cm):
        """Different anchors get different colors."""
        c1 = cm.get_color(_anchor("x", line=1))
        c2 = cm.get_color(_anchor("y", line=2))
        assert c1.name() != c2.name()

    def test_deterministic_across_instances(self, qapp):
        """Two fresh ColorManagers assign the same first color."""
        cm1 = ColorManager()
        cm2 = ColorManager()
        a = _anchor("x")
        assert cm1.get_color(a).name() == cm2.get_color(a).name()


class TestColorRelease:
    def test_release_makes_color_available(self, cm):
        """Releasing a color makes the slot available again."""
        a = _anchor("x")
        cm.get_color(a)
        initial_available = cm.available_count
        cm.release_color(a)
        assert cm.available_count == initial_available + 1

    def test_release_unknown_anchor_no_error(self, cm):
        """Releasing unknown anchor doesn't raise."""
        cm.release_color(_anchor("nonexistent"))


class TestColorCycling:
    def test_palette_exhaustion_raises(self, cm):
        """Exhausting palette raises ValueError."""
        # Assign all colors
        for i in range(ColorManager.MAX_PROBES):
            cm.get_color(_anchor(f"v{i}", line=i))

        with pytest.raises(ValueError, match="No colors available"):
            cm.get_color(_anchor("overflow", line=999))

    def test_release_and_reassign(self, cm):
        """After releasing, the slot can be reused."""
        anchors = [_anchor(f"v{i}", line=i) for i in range(ColorManager.MAX_PROBES)]
        for a in anchors:
            cm.get_color(a)

        # Release one
        cm.release_color(anchors[0])
        # Should not raise
        new_color = cm.get_color(_anchor("new", line=1000))
        assert isinstance(new_color, QColor)


class TestLRUEmphasis:
    def test_newest_has_full_emphasis(self, cm):
        """Most recently accessed anchor has emphasis 1.0."""
        a = _anchor("x")
        cm.get_color(a)
        assert cm.get_emphasis_level(a) == 1.0

    def test_older_has_lower_emphasis(self, cm):
        """Older anchor has lower emphasis than newer."""
        a1 = _anchor("old", line=1)
        a2 = _anchor("new", line=2)
        cm.get_color(a1)
        cm.get_color(a2)

        assert cm.get_emphasis_level(a1) < cm.get_emphasis_level(a2)

    def test_accessing_moves_to_end(self, cm):
        """Re-accessing an anchor bumps its emphasis."""
        a1 = _anchor("x", line=1)
        a2 = _anchor("y", line=2)
        cm.get_color(a1)
        cm.get_color(a2)

        # a1 is now oldest
        assert cm.get_emphasis_level(a1) < cm.get_emphasis_level(a2)

        # Access a1 again -> now newest
        cm.get_color(a1)
        assert cm.get_emphasis_level(a1) >= cm.get_emphasis_level(a2)


class TestColorManagerState:
    def test_has_color(self, cm):
        """has_color returns True after assignment."""
        a = _anchor("x")
        assert not cm.has_color(a)
        cm.get_color(a)
        assert cm.has_color(a)

    def test_assigned_count(self, cm):
        """assigned_count tracks number of assignments."""
        assert cm.assigned_count == 0
        cm.get_color(_anchor("x"))
        assert cm.assigned_count == 1
        cm.get_color(_anchor("y", line=2))
        assert cm.assigned_count == 2
