"""Unit tests for AxisEditor."""

import pytest
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from pyprobe.gui.axis_editor import AxisEditor


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def editor(app):
    return AxisEditor()


class TestAxisEditorDisplay:
    def test_initially_hidden(self, editor):
        assert not editor.isVisible()

    def test_show_at_makes_visible(self, editor):
        editor.show_at(100, 100, 42.0)
        assert editor.isVisible()

    def test_show_at_sets_text(self, editor):
        editor.show_at(100, 100, 3.14)
        assert "3.14" in editor.text()

    def test_show_at_scientific_notation(self, editor):
        editor.show_at(100, 100, 0.001)
        assert "e" in editor.text().lower() or "0.001" in editor.text()


class TestAxisEditorCommit:
    def test_commit_emits_value(self, editor):
        received = []
        editor.value_committed.connect(received.append)
        editor.show_at(100, 100, 0.0)
        editor.setText("42.5")
        QTest.keyClick(editor, Qt.Key.Key_Return)
        assert len(received) == 1
        assert received[0] == 42.5

    def test_commit_hides(self, editor):
        editor.show_at(100, 100, 0.0)
        editor.setText("10.0")
        QTest.keyClick(editor, Qt.Key.Key_Return)
        assert not editor.isVisible()


class TestAxisEditorCancel:
    def test_escape_cancels(self, editor):
        cancelled = []
        editor.editing_cancelled.connect(lambda: cancelled.append(True))
        editor.show_at(100, 100, 5.0)
        QTest.keyClick(editor, Qt.Key.Key_Escape)
        assert len(cancelled) == 1
        assert not editor.isVisible()
