"""Tests for probe highlight and gutter eye icon lifecycle.

Covers two regression scenarios:
1. Re-probing a variable after closing its panel restores the highlight
   and gutter eye icon.
2. The gutter eye icon persists when one probe on a line is removed but
   another probe on the same line remains active.
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


def _find_close_button(panel) -> QPushButton:
    """Find the close button on a probe panel."""
    for child in panel.findChildren(QPushButton):
        if child.text() == "\u00d7":
            return child
    raise RuntimeError("Close button not found on panel")


def _close_panel(qtbot, panel):
    """Click the close button on a panel and wait for async cleanup."""
    close_btn = _find_close_button(panel)
    qtbot.mouseClick(close_btn, Qt.MouseButton.LeftButton)
    qtbot.wait(500)


# ---------------------------------------------------------------------------
# Bug 1: Re-probe after panel close must restore highlight + gutter eye
# ---------------------------------------------------------------------------

class TestReprobeRestoresHighlight:
    """Closing a panel and re-probing the same variable must restore visuals."""

    def test_highlight_restored_after_close_and_reprobe(self, main_window, qtbot):
        """Code viewer highlight reappears when re-probing after panel close."""
        anchor = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")
        viewer = main_window._code_viewer

        # Probe -> highlight exists
        main_window._on_probe_requested(anchor)
        assert anchor in viewer._active_probes

        # Close panel -> highlight removed by global unprobe
        panel = main_window._probe_container.get_all_panels()[0]
        _close_panel(qtbot, panel)
        assert anchor not in viewer._active_probes

        # Re-probe -> highlight must come back
        main_window._on_probe_requested(anchor)
        assert anchor in viewer._active_probes

    def test_graphical_flag_restored_after_close_and_reprobe(self, main_window, qtbot):
        """Code viewer graphical probe flag is restored on re-probe."""
        anchor = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")
        viewer = main_window._code_viewer

        main_window._on_probe_requested(anchor)
        assert viewer.has_graphical_probe(anchor)

        panel = main_window._probe_container.get_all_panels()[0]
        _close_panel(qtbot, panel)
        assert not viewer.has_graphical_probe(anchor)

        main_window._on_probe_requested(anchor)
        assert viewer.has_graphical_probe(anchor)

    def test_gutter_eye_restored_after_close_and_reprobe(self, main_window, qtbot):
        """Gutter eye icon reappears when re-probing after panel close."""
        anchor = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")
        gutter = main_window._code_gutter

        main_window._on_probe_requested(anchor)
        assert anchor.line in gutter._probed_lines

        panel = main_window._probe_container.get_all_panels()[0]
        _close_panel(qtbot, panel)
        assert anchor.line not in gutter._probed_lines

        main_window._on_probe_requested(anchor)
        assert anchor.line in gutter._probed_lines

    def test_registry_active_after_close_and_reprobe(self, main_window, qtbot):
        """Probe registry tracks the anchor as active after re-probe."""
        anchor = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")

        main_window._on_probe_requested(anchor)
        assert anchor in main_window._probe_registry.active_anchors

        panel = main_window._probe_container.get_all_panels()[0]
        _close_panel(qtbot, panel)
        assert anchor not in main_window._probe_registry.active_anchors

        main_window._on_probe_requested(anchor)
        assert anchor in main_window._probe_registry.active_anchors

    def test_new_panel_created_after_close_and_reprobe(self, main_window, qtbot):
        """A new panel is created in the container on re-probe."""
        anchor = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")

        main_window._on_probe_requested(anchor)
        assert len(main_window._probe_container.get_all_panels()) == 1

        panel = main_window._probe_container.get_all_panels()[0]
        _close_panel(qtbot, panel)
        assert len(main_window._probe_container.get_all_panels()) == 0

        main_window._on_probe_requested(anchor)
        assert len(main_window._probe_container.get_all_panels()) == 1


# ---------------------------------------------------------------------------
# Bug 2: Gutter eye must persist while any probe on the line is active
# ---------------------------------------------------------------------------

class TestGutterEyePerLine:
    """The gutter eye icon is line-level and must stay while any probe on
    that line remains active."""

    def test_eye_persists_when_one_of_two_probes_removed(self, main_window, qtbot):
        """Removing one probe on a line keeps the eye if another is active."""
        anchor_a = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")
        anchor_b = ProbeAnchor(file="test.py", line=10, col=8, symbol="y")
        gutter = main_window._code_gutter

        # Probe both variables on the same line
        main_window._on_probe_requested(anchor_a)
        main_window._on_probe_requested(anchor_b)
        assert anchor_a.line in gutter._probed_lines

        # Close the first panel -> eye must remain
        panels = main_window._probe_container.get_all_panels()
        # Find the panel for anchor_a
        panel_a = None
        for p in panels:
            if p._anchor == anchor_a:
                panel_a = p
                break
        assert panel_a is not None
        _close_panel(qtbot, panel_a)

        assert anchor_a.line in gutter._probed_lines, \
            "Gutter eye disappeared even though another probe on the same line is active"

    def test_eye_removed_when_last_probe_on_line_removed(self, main_window, qtbot):
        """Eye disappears only after the last probe on the line is removed."""
        anchor_a = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")
        anchor_b = ProbeAnchor(file="test.py", line=10, col=8, symbol="y")
        gutter = main_window._code_gutter

        main_window._on_probe_requested(anchor_a)
        main_window._on_probe_requested(anchor_b)

        # Close first panel
        panel_a = None
        for p in main_window._probe_container.get_all_panels():
            if p._anchor == anchor_a:
                panel_a = p
                break
        _close_panel(qtbot, panel_a)
        assert anchor_a.line in gutter._probed_lines  # still there

        # Close second panel -> now the line should be clear
        panel_b = main_window._probe_container.get_all_panels()[0]
        _close_panel(qtbot, panel_b)
        assert anchor_b.line not in gutter._probed_lines

    def test_probes_on_different_lines_independent(self, main_window, qtbot):
        """Removing a probe on one line does not affect the gutter eye on another."""
        anchor_l10 = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")
        anchor_l20 = ProbeAnchor(file="test.py", line=20, col=0, symbol="y")
        gutter = main_window._code_gutter

        main_window._on_probe_requested(anchor_l10)
        main_window._on_probe_requested(anchor_l20)
        assert 10 in gutter._probed_lines
        assert 20 in gutter._probed_lines

        # Close the line-10 panel
        panel_l10 = None
        for p in main_window._probe_container.get_all_panels():
            if p._anchor == anchor_l10:
                panel_l10 = p
                break
        _close_panel(qtbot, panel_l10)

        assert 10 not in gutter._probed_lines
        assert 20 in gutter._probed_lines
