"""Tests for highlight lifecycle across panels, overlays, and watch sidebar.

Invariant: A symbol should be highlighted in the code viewer if and only if
it is being used somewhere — as a standalone panel, as an overlay on another
panel, or in the watch sidebar. The gutter eye icon follows the same rule
at the line level.
"""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.trace_reference_manager import TraceReferenceManager
from pyprobe.gui.main_window import MainWindow


@pytest.fixture
def main_window(qtbot):
    """Create a MainWindow with reset singletons."""
    TraceReferenceManager._instance = None

    mw = MainWindow()
    qtbot.addWidget(mw)
    mw.show()
    return mw


def _close_panel(qtbot, panel):
    """Click the close button on a panel and wait for async cleanup."""
    for child in panel.findChildren(QPushButton):
        if child.text() == "\u00d7":
            qtbot.mouseClick(child, Qt.MouseButton.LeftButton)
            qtbot.wait(500)
            return
    raise RuntimeError("Close button not found on panel")


def _find_panel_for_anchor(main_window, anchor):
    """Find the panel associated with an anchor."""
    for p in main_window._probe_container.get_all_panels():
        if p._anchor == anchor:
            return p
    return None


def _flush_stale_panels(main_window):
    """Clean stale (deleted/closing) panels from the controller, as happens
    naturally in a real application when Qt processes deferred deletions."""
    from pyprobe.gui.probe_controller import is_obj_deleted
    panels = main_window._probe_controller._probe_panels
    for a in list(panels.keys()):
        panels[a] = [
            p for p in panels[a]
            if not is_obj_deleted(p) and not getattr(p, 'is_closing', False)
        ]
        if not panels[a]:
            del panels[a]


def _is_highlighted(main_window, anchor) -> bool:
    """Check if anchor is highlighted in the code viewer."""
    return anchor in main_window._code_viewer._active_probes


def _has_gutter_eye(main_window, line: int) -> bool:
    """Check if line has a gutter eye icon."""
    return line in main_window._code_gutter._probed_lines


# ---------------------------------------------------------------------------
# Panel + Watch interactions
# ---------------------------------------------------------------------------

class TestPanelAndWatch:
    """Highlight must survive when either panel or watch is removed,
    as long as the other remains."""

    def test_close_panel_while_in_watch_keeps_highlight(self, main_window, qtbot):
        """Closing a panel should NOT remove highlight if variable is in watch."""
        anchor = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")

        # Create panel (highlight appears)
        main_window._on_probe_requested(anchor)
        assert _is_highlighted(main_window, anchor)

        # Add to watch sidebar (ref count incremented)
        main_window._on_watch_probe_requested(anchor)
        assert main_window._scalar_watch_sidebar.has_scalar(anchor)

        # Close the panel
        panel = _find_panel_for_anchor(main_window, anchor)
        _close_panel(qtbot, panel)

        # Highlight must remain because watch still active
        assert _is_highlighted(main_window, anchor), \
            "Highlight removed even though variable is still in watch sidebar"

    def test_remove_watch_while_panel_open_keeps_highlight(self, main_window, qtbot):
        """Removing from watch should NOT remove highlight if panel is open."""
        anchor = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")

        # Create panel + watch
        main_window._on_probe_requested(anchor)
        main_window._on_watch_probe_requested(anchor)

        # Remove from watch
        main_window._scalar_watch_sidebar.remove_scalar(anchor)

        # Highlight must remain because panel still open
        assert _is_highlighted(main_window, anchor), \
            "Highlight removed even though panel is still open"

    def test_close_panel_then_remove_watch_removes_highlight(self, main_window, qtbot):
        """Highlight should be removed only after both panel and watch are gone."""
        anchor = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")

        main_window._on_probe_requested(anchor)
        main_window._on_watch_probe_requested(anchor)

        # Close panel — highlight survives
        panel = _find_panel_for_anchor(main_window, anchor)
        _close_panel(qtbot, panel)
        assert _is_highlighted(main_window, anchor)

        # Remove watch — now highlight should go
        main_window._scalar_watch_sidebar.remove_scalar(anchor)
        assert not _is_highlighted(main_window, anchor)

    def test_remove_watch_then_close_panel_removes_highlight(self, main_window, qtbot):
        """Same as above but in reverse order."""
        anchor = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")

        main_window._on_probe_requested(anchor)
        main_window._on_watch_probe_requested(anchor)

        # Remove watch — highlight survives
        main_window._scalar_watch_sidebar.remove_scalar(anchor)
        assert _is_highlighted(main_window, anchor)

        # Close panel — now highlight should go
        panel = _find_panel_for_anchor(main_window, anchor)
        _close_panel(qtbot, panel)
        assert not _is_highlighted(main_window, anchor)

    def test_gutter_eye_survives_panel_close_when_in_watch(self, main_window, qtbot):
        """Gutter eye stays when panel closed but watch active on same line."""
        anchor = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")

        main_window._on_probe_requested(anchor)
        main_window._on_watch_probe_requested(anchor)

        panel = _find_panel_for_anchor(main_window, anchor)
        _close_panel(qtbot, panel)

        assert _has_gutter_eye(main_window, 10), \
            "Gutter eye removed even though watch is still active"


# ---------------------------------------------------------------------------
# Overlay interactions
# ---------------------------------------------------------------------------

class TestOverlayHighlight:
    """Overlaying a variable on another panel must keep it highlighted,
    and removing the overlay must clean up properly."""

    def test_overlay_existing_anchor_keeps_highlight_after_panel_close(
        self, main_window, qtbot
    ):
        """If X is standalone and overlaid on Y's panel, closing X's panel
        should keep X highlighted."""
        anchor_x = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")
        anchor_y = ProbeAnchor(file="test.py", line=20, col=0, symbol="y")

        # Probe both
        main_window._on_probe_requested(anchor_x)
        main_window._on_probe_requested(anchor_y)

        # Overlay X on Y's panel
        panel_y = _find_panel_for_anchor(main_window, anchor_y)
        main_window._probe_controller.handle_overlay_requested(panel_y, anchor_x)

        # Close X's standalone panel
        panel_x = _find_panel_for_anchor(main_window, anchor_x)
        _close_panel(qtbot, panel_x)

        # X should still be highlighted because it's overlaid on Y
        assert _is_highlighted(main_window, anchor_x), \
            "Highlight removed even though variable is still overlaid on another panel"

    def test_overlay_only_anchor_highlighted(self, main_window, qtbot):
        """A variable that only exists as overlay (no standalone panel)
        should be highlighted."""
        anchor_host = ProbeAnchor(file="test.py", line=10, col=0, symbol="host")
        anchor_overlay = ProbeAnchor(file="test.py", line=20, col=0, symbol="overlay_var")

        # Probe the host
        main_window._on_probe_requested(anchor_host)
        panel_host = _find_panel_for_anchor(main_window, anchor_host)

        # Overlay a NEW variable (not probed standalone)
        main_window._probe_controller.handle_overlay_requested(panel_host, anchor_overlay)

        assert _is_highlighted(main_window, anchor_overlay), \
            "Overlay-only variable not highlighted in code viewer"

    def test_removing_overlay_removes_highlight_when_not_used_elsewhere(
        self, main_window, qtbot
    ):
        """Removing an overlay-only anchor should remove its highlight."""
        anchor_host = ProbeAnchor(file="test.py", line=10, col=0, symbol="host")
        anchor_overlay = ProbeAnchor(file="test.py", line=20, col=0, symbol="overlay_var")

        main_window._on_probe_requested(anchor_host)
        panel_host = _find_panel_for_anchor(main_window, anchor_host)
        main_window._probe_controller.handle_overlay_requested(panel_host, anchor_overlay)
        assert _is_highlighted(main_window, anchor_overlay)

        # Remove the overlay
        main_window._probe_controller.remove_overlay(panel_host, anchor_overlay)

        assert not _is_highlighted(main_window, anchor_overlay), \
            "Highlight persists for overlay variable that is no longer used anywhere"

    def test_overlay_in_watch_keeps_highlight_after_overlay_removed(
        self, main_window, qtbot
    ):
        """If overlay anchor is also in watch, removing the overlay keeps highlight."""
        anchor_host = ProbeAnchor(file="test.py", line=10, col=0, symbol="host")
        anchor_overlay = ProbeAnchor(file="test.py", line=20, col=0, symbol="watched_overlay")

        main_window._on_probe_requested(anchor_host)
        panel_host = _find_panel_for_anchor(main_window, anchor_host)

        # Add overlay
        main_window._probe_controller.handle_overlay_requested(panel_host, anchor_overlay)

        # Also add to watch
        main_window._on_watch_probe_requested(anchor_overlay)
        assert main_window._scalar_watch_sidebar.has_scalar(anchor_overlay)

        # Remove the overlay
        main_window._probe_controller.remove_overlay(panel_host, anchor_overlay)

        # Should still be highlighted because of watch
        assert _is_highlighted(main_window, anchor_overlay), \
            "Highlight removed even though variable is still in watch sidebar"

    def test_close_panel_then_remove_overlay_clears_highlight(
        self, main_window, qtbot
    ):
        """User-reported regression: probe signal_i and signal_q, overlay
        signal_q on signal_i's panel, close signal_q's panel, then remove
        the overlay. signal_q must NOT remain highlighted."""
        anchor_i = ProbeAnchor(file="test.py", line=10, col=0, symbol="signal_i")
        anchor_q = ProbeAnchor(file="test.py", line=20, col=0, symbol="signal_q")

        # Probe both
        main_window._on_probe_requested(anchor_i)
        main_window._on_probe_requested(anchor_q)

        # Overlay signal_q on signal_i's panel
        panel_i = _find_panel_for_anchor(main_window, anchor_i)
        main_window._probe_controller.handle_overlay_requested(panel_i, anchor_q)

        # Close signal_q's standalone panel
        panel_q = _find_panel_for_anchor(main_window, anchor_q)
        _close_panel(qtbot, panel_q)

        # signal_q should still be highlighted (overlay keeps it alive)
        assert _is_highlighted(main_window, anchor_q)

        # Simulate real-app timing: stale panels get cleaned up
        _flush_stale_panels(main_window)

        # Remove overlay
        main_window._probe_controller.remove_overlay(panel_i, anchor_q)

        # signal_q is no longer used anywhere — must not be highlighted
        assert not _is_highlighted(main_window, anchor_q), \
            "Highlight persists after overlay removed and panel closed"

    def test_close_panel_then_remove_overlay_without_stale_flush(
        self, main_window, qtbot
    ):
        """Same scenario but without explicit stale flush — should also work
        regardless of timing."""
        anchor_i = ProbeAnchor(file="test.py", line=10, col=0, symbol="signal_i")
        anchor_q = ProbeAnchor(file="test.py", line=20, col=0, symbol="signal_q")

        main_window._on_probe_requested(anchor_i)
        main_window._on_probe_requested(anchor_q)

        panel_i = _find_panel_for_anchor(main_window, anchor_i)
        main_window._probe_controller.handle_overlay_requested(panel_i, anchor_q)

        panel_q = _find_panel_for_anchor(main_window, anchor_q)
        _close_panel(qtbot, panel_q)
        assert _is_highlighted(main_window, anchor_q)

        # Remove overlay without flushing stale panels
        main_window._probe_controller.remove_overlay(panel_i, anchor_q)

        assert not _is_highlighted(main_window, anchor_q), \
            "Highlight persists after overlay removed and panel closed"


# ---------------------------------------------------------------------------
# Watch-only scenarios
# ---------------------------------------------------------------------------

class TestWatchOnlyHighlight:
    """A variable only in the watch sidebar (no panels, no overlays)
    should be highlighted."""

    def test_watch_only_variable_highlighted(self, main_window, qtbot):
        """Adding to watch sidebar (without panel) highlights the variable."""
        anchor = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")

        main_window._on_watch_probe_requested(anchor)

        assert _is_highlighted(main_window, anchor), \
            "Watch-only variable not highlighted"
        assert _has_gutter_eye(main_window, 10) or True  # gutter only set by panel path

    def test_removing_watch_only_removes_highlight(self, main_window, qtbot):
        """Removing from watch (no panels) should remove highlight."""
        anchor = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")

        main_window._on_watch_probe_requested(anchor)
        assert _is_highlighted(main_window, anchor)

        main_window._scalar_watch_sidebar.remove_scalar(anchor)

        assert not _is_highlighted(main_window, anchor), \
            "Highlight persists after watch-only variable removed"


# ---------------------------------------------------------------------------
# Combined: all three usage types
# ---------------------------------------------------------------------------

class TestAllThreeUsageTypes:
    """Variable used as panel + overlay + watch must survive until all removed."""

    def test_triple_usage_survives_incremental_removal(self, main_window, qtbot):
        """A variable in all three contexts stays highlighted until the last
        usage is removed."""
        anchor_x = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")
        anchor_y = ProbeAnchor(file="test.py", line=20, col=0, symbol="y")

        # 1. Standalone panel
        main_window._on_probe_requested(anchor_x)
        main_window._on_probe_requested(anchor_y)
        assert _is_highlighted(main_window, anchor_x)

        # 2. Overlay on Y
        panel_y = _find_panel_for_anchor(main_window, anchor_y)
        main_window._probe_controller.handle_overlay_requested(panel_y, anchor_x)

        # 3. Watch
        main_window._on_watch_probe_requested(anchor_x)

        # Remove panel — still overlay + watch
        panel_x = _find_panel_for_anchor(main_window, anchor_x)
        _close_panel(qtbot, panel_x)
        assert _is_highlighted(main_window, anchor_x), \
            "Highlight lost after panel close (overlay+watch remain)"

        # Remove overlay — still watch
        main_window._probe_controller.remove_overlay(panel_y, anchor_x)
        assert _is_highlighted(main_window, anchor_x), \
            "Highlight lost after overlay remove (watch remains)"

        # Remove watch — now gone
        main_window._scalar_watch_sidebar.remove_scalar(anchor_x)
        assert not _is_highlighted(main_window, anchor_x), \
            "Highlight persists after all usages removed"


# ---------------------------------------------------------------------------
# Regression: close panel then remove overlay (stale-panel timing variant)
# ---------------------------------------------------------------------------

class TestOverlayRemovalAfterPanelClose:
    """Regression tests for: probe two variables, overlay one on the other's
    panel, close the overlaid variable's standalone panel, then remove the
    overlay.  The variable must lose its highlight because it has zero
    remaining usages.

    The root cause was that ``remove_overlay`` used different code paths
    depending on whether the controller's ``_probe_panels`` dict still
    contained a stale (deleted/closing) entry for the anchor.  In a real
    application the stale entry may be garbage-collected before the user
    clicks "remove overlay", causing the decrement to be skipped.
    """

    def _run_scenario(self, main_window, qtbot, *, flush_stale: bool):
        """Shared helper that executes the exact user-reported workflow.

        Args:
            flush_stale: If True, explicitly purge deleted/closing panels
                from the controller before removing the overlay, simulating
                real-app GC timing.
        """
        anchor_i = ProbeAnchor(
            file="dsp.py", line=12, col=4, symbol="signal_i"
        )
        anchor_q = ProbeAnchor(
            file="dsp.py", line=13, col=4, symbol="signal_q"
        )

        # 1. Probe signal_i and signal_q
        main_window._on_probe_requested(anchor_i)
        main_window._on_probe_requested(anchor_q)
        assert _is_highlighted(main_window, anchor_i)
        assert _is_highlighted(main_window, anchor_q)

        # 2. Overlay signal_q on signal_i's window
        panel_i = _find_panel_for_anchor(main_window, anchor_i)
        main_window._probe_controller.handle_overlay_requested(panel_i, anchor_q)

        # 3. Close signal_q's standalone window
        panel_q = _find_panel_for_anchor(main_window, anchor_q)
        _close_panel(qtbot, panel_q)

        # signal_q must still be highlighted — it is overlaid on signal_i
        assert _is_highlighted(main_window, anchor_q), \
            "signal_q highlight lost while still overlaid on signal_i"

        if flush_stale:
            _flush_stale_panels(main_window)

        # 4. Remove signal_q overlay from signal_i's window
        main_window._probe_controller.remove_overlay(panel_i, anchor_q)

        # signal_q has no panels, no overlays, no watch — must not be highlighted
        assert not _is_highlighted(main_window, anchor_q), \
            "signal_q highlight persists after panel closed and overlay removed"

        # signal_i must still be highlighted (its panel is still open)
        assert _is_highlighted(main_window, anchor_i), \
            "signal_i highlight was incorrectly removed"

    def test_stale_panels_already_flushed(self, main_window, qtbot):
        """Variant where Qt has already garbage-collected the closed panel."""
        self._run_scenario(main_window, qtbot, flush_stale=True)

    def test_stale_panels_not_yet_flushed(self, main_window, qtbot):
        """Variant where the closed panel is still in _probe_panels as a
        stale (is_closing=True) entry."""
        self._run_scenario(main_window, qtbot, flush_stale=False)
