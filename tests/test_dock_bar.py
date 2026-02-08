"""Unit tests for DockBar."""

import pytest
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor

from pyprobe.gui.dock_bar import DockBar, DockBarItem


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def dock_bar(app):
    return DockBar()


class TestDockBarEmpty:
    def test_initially_empty(self, dock_bar):
        assert dock_bar.is_empty()

    def test_initially_hidden(self, dock_bar):
        assert not dock_bar.isVisible()


class TestDockBarAddRemove:
    def test_add_panel_not_empty(self, dock_bar):
        dock_bar.add_panel("key1", "Signal A", QColor("cyan"))
        assert not dock_bar.is_empty()

    def test_add_panel_visible(self, dock_bar):
        dock_bar.add_panel("key2", "Signal B", QColor("magenta"))
        assert dock_bar.isVisible()

    def test_remove_panel(self, dock_bar):
        dock_bar.add_panel("key3", "Signal C", QColor("yellow"))
        dock_bar.remove_panel("key3")
        assert "key3" not in dock_bar._items

    def test_remove_all_hides(self, dock_bar):
        bar = DockBar()
        bar.add_panel("k1", "A", QColor("cyan"))
        bar.remove_panel("k1")
        assert bar.is_empty()
        assert not bar.isVisible()

    def test_duplicate_add_ignored(self, dock_bar):
        dock_bar.add_panel("dup", "X", QColor("red"))
        dock_bar.add_panel("dup", "X", QColor("red"))
        assert len([k for k in dock_bar._items if k == "dup"]) == 1


class TestDockBarRestore:
    def test_restore_signal(self, dock_bar):
        keys = []
        dock_bar.panel_restore_requested.connect(keys.append)
        dock_bar.add_panel("restore_key", "Test", QColor("cyan"))
        # Simulate click
        dock_bar._items["restore_key"].restore_requested.emit()
        assert "restore_key" in keys
