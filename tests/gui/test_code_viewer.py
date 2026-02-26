"""Tests for CodeViewer highlight_changed signal."""

import pytest
from PyQt6.QtGui import QColor

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.gui.code_viewer import CodeViewer


def _make_anchor(symbol="x", line=1, col=0):
    return ProbeAnchor(
        file="test.py", line=line, col=col,
        symbol=symbol, func="", is_assignment=False,
    )


# ── highlight_changed signal tests ───────────────────────────────────────────


def test_highlight_changed_emits_true_on_first_activation(qtbot):
    """highlight_changed emits (anchor, True) when a new anchor is first added."""
    viewer = CodeViewer()
    qtbot.addWidget(viewer)
    anchor = _make_anchor()
    color = QColor("#00ff00")

    with qtbot.waitSignal(viewer.highlight_changed, timeout=1000) as blocker:
        viewer.set_probe_active(anchor, color)

    assert blocker.args == [anchor, True]


def test_highlight_changed_no_emit_on_ref_count_increment(qtbot):
    """highlight_changed does NOT emit when ref_count is incremented (already active)."""
    viewer = CodeViewer()
    qtbot.addWidget(viewer)
    anchor = _make_anchor()
    color = QColor("#00ff00")

    # First activation — emits
    viewer.set_probe_active(anchor, color)

    # Second activation — should NOT emit
    emissions = []
    viewer.highlight_changed.connect(lambda a, h: emissions.append((a, h)))
    viewer.set_probe_active(anchor, color)
    assert len(emissions) == 0


def test_highlight_changed_emits_false_on_last_removal(qtbot):
    """highlight_changed emits (anchor, False) when the last reference is removed."""
    viewer = CodeViewer()
    qtbot.addWidget(viewer)
    anchor = _make_anchor()
    color = QColor("#00ff00")
    viewer.set_probe_active(anchor, color)

    with qtbot.waitSignal(viewer.highlight_changed, timeout=1000) as blocker:
        viewer.remove_probe(anchor)

    assert blocker.args == [anchor, False]


def test_highlight_changed_no_emit_on_ref_count_decrement(qtbot):
    """highlight_changed does NOT emit when ref_count goes from 2 to 1."""
    viewer = CodeViewer()
    qtbot.addWidget(viewer)
    anchor = _make_anchor()
    color = QColor("#00ff00")

    # Add twice (ref_count = 2)
    viewer.set_probe_active(anchor, color)
    viewer.set_probe_active(anchor, color)

    # Remove once — goes from 2 → 1, should NOT emit
    emissions = []
    viewer.highlight_changed.connect(lambda a, h: emissions.append((a, h)))
    viewer.remove_probe(anchor)
    assert len(emissions) == 0
