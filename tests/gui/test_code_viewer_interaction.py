"""Phase 3.1: Code viewer interaction tests.

Verifies click-to-probe, click-to-remove, and Alt+click-to-watch signals.
"""

import os
import tempfile
import pytest
from unittest.mock import MagicMock
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QColor

from pyprobe.gui.code_viewer import CodeViewer
from pyprobe.core.anchor import ProbeAnchor


SAMPLE_CODE = """\
def process():
    x = 42
    y = x + 1
    return y
"""


@pytest.fixture
def code_file():
    """Write sample code to a temp file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(SAMPLE_CODE)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def viewer(qapp, code_file):
    """Create and configure a CodeViewer with loaded file."""
    v = CodeViewer()
    v.resize(600, 400)
    v.show()
    qapp.processEvents()
    v.load_file(code_file)
    qapp.processEvents()
    return v


class TestClickToProbe:
    def test_click_on_variable_emits_probe_requested(self, viewer, qapp):
        """Clicking on a variable emits probe_requested signal."""
        received = []
        viewer.probe_requested.connect(lambda a: received.append(a))

        # Find position of 'x' on line 2 (0-indexed: line 1, col 4)
        # Use cursor-based positioning
        cursor = viewer.textCursor()
        block = viewer.document().findBlockByLineNumber(1)  # line 2 (0-indexed)
        cursor.setPosition(block.position() + 4)  # col 4 = 'x'
        rect = viewer.cursorRect(cursor)
        click_pos = rect.center()

        # Simulate mouse press and release (click)
        QTest.mousePress(viewer.viewport(), Qt.MouseButton.LeftButton, pos=click_pos)
        qapp.processEvents()
        QTest.mouseRelease(viewer.viewport(), Qt.MouseButton.LeftButton, pos=click_pos)
        qapp.processEvents()

        assert len(received) >= 1
        assert received[0].symbol == 'x'

    def test_click_on_active_probe_emits_remove(self, viewer, qapp):
        """Clicking an active graphical probe emits probe_removed."""
        # First, find and click 'x' to create a probe
        cursor = viewer.textCursor()
        block = viewer.document().findBlockByLineNumber(1)
        cursor.setPosition(block.position() + 4)
        rect = viewer.cursorRect(cursor)
        click_pos = rect.center()

        # Simulate first click (creates probe)
        requested = []
        viewer.probe_requested.connect(lambda a: requested.append(a))
        QTest.mousePress(viewer.viewport(), Qt.MouseButton.LeftButton, pos=click_pos)
        qapp.processEvents()
        QTest.mouseRelease(viewer.viewport(), Qt.MouseButton.LeftButton, pos=click_pos)
        qapp.processEvents()

        if not requested:
            pytest.skip("Could not create probe on 'x'")

        anchor = requested[0]
        # Mark it as active + graphical
        viewer.set_probe_active(anchor, QColor("#00ffff"))
        viewer.set_probe_graphical(anchor)
        qapp.processEvents()

        # Click again -> should emit probe_removed
        removed = []
        viewer.probe_removed.connect(lambda a: removed.append(a))
        QTest.mousePress(viewer.viewport(), Qt.MouseButton.LeftButton, pos=click_pos)
        qapp.processEvents()
        QTest.mouseRelease(viewer.viewport(), Qt.MouseButton.LeftButton, pos=click_pos)
        qapp.processEvents()

        assert len(removed) >= 1
        assert removed[0].symbol == anchor.symbol

    def test_alt_click_emits_watch(self, viewer, qapp):
        """Alt+click emits watch_probe_requested signal."""
        watch_received = []
        viewer.watch_probe_requested.connect(lambda a: watch_received.append(a))

        cursor = viewer.textCursor()
        block = viewer.document().findBlockByLineNumber(1)
        cursor.setPosition(block.position() + 4)
        rect = viewer.cursorRect(cursor)
        click_pos = rect.center()

        QTest.mousePress(
            viewer.viewport(), Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.AltModifier, click_pos
        )
        qapp.processEvents()
        QTest.mouseRelease(
            viewer.viewport(), Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.AltModifier, click_pos
        )
        qapp.processEvents()

        assert len(watch_received) >= 1
        assert watch_received[0].symbol == 'x'
