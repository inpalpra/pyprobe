"""Tests for probe highlight and gutter eye icon lifecycle.

Covers two regression scenarios:
1. Re-probing a variable after closing its panel restores the highlight
   and gutter eye icon.
2. The gutter eye icon persists when one probe on a line is removed but
   another probe on the same line remains active.

FAST VERSION: Consolidates assertions into fewer test runs to minimize heavy
MainWindow instantiations.
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

    def test_reprobe_restores_all_visuals_and_state(self, main_window, qtbot):
        """Code viewer highlight, graphical flag, gutter eye, and registry
        all restore when re-probing after panel close.
        (Consolidated from 5 individual tests for speed).
        """
        anchor = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")
        viewer = main_window._code_viewer
        gutter = main_window._code_gutter
        registry = main_window._probe_registry
        container = main_window._probe_container

        # 1. Initial Probe
        main_window._on_probe_requested(anchor)

        assert anchor in viewer._active_probes
        assert viewer.has_graphical_probe(anchor)
        assert anchor.line in gutter._probed_lines
        assert anchor in registry.active_anchors
        assert len(container.get_all_panels()) == 1

        # 2. Close panel
        panel = container.get_all_panels()[0]
        _close_panel(qtbot, panel)

        assert anchor not in viewer._active_probes
        assert not viewer.has_graphical_probe(anchor)
        assert anchor.line not in gutter._probed_lines
        assert anchor not in registry.active_anchors
        assert len(container.get_all_panels()) == 0

        # 3. Re-probe
        main_window._on_probe_requested(anchor)

        assert anchor in viewer._active_probes
        assert viewer.has_graphical_probe(anchor)
        assert anchor.line in gutter._probed_lines
        assert anchor in registry.active_anchors
        assert len(container.get_all_panels()) == 1


# ---------------------------------------------------------------------------
# Bug 2: Gutter eye must persist while any probe on the line is active
# ---------------------------------------------------------------------------

class TestGutterEyePerLine:
    """The gutter eye icon is line-level and must stay while any probe on
    that line remains active."""

    def test_eye_persists_then_removed_progressively(self, main_window, qtbot):
        """Removing one probe keeps the eye, removing the last one clears it.
        (Consolidated from 2 individual tests for speed).
        """
        anchor_a = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")
        anchor_b = ProbeAnchor(file="test.py", line=10, col=8, symbol="y")
        gutter = main_window._code_gutter
        container = main_window._probe_container

        # Probe both variables on the same line
        main_window._on_probe_requested(anchor_a)
        main_window._on_probe_requested(anchor_b)
        assert anchor_a.line in gutter._probed_lines

        # Close the first panel -> eye must remain
        panels = container.get_all_panels()
        panel_a = next(p for p in panels if p._anchor == anchor_a)
        _close_panel(qtbot, panel_a)

        assert anchor_a.line in gutter._probed_lines, \
            "Gutter eye disappeared even though another probe on the same line is active"

        # Close second panel -> now the line should be clear
        panel_b = container.get_all_panels()[0]
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
