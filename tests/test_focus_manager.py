"""Unit tests for FocusManager."""

import pytest
import sys
from PyQt6.QtWidgets import QApplication, QWidget

from pyprobe.gui.focus_manager import FocusManager


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def manager(app):
    return FocusManager()


@pytest.fixture
def panels(app):
    return [QWidget(), QWidget(), QWidget()]


class TestFocusManagerInit:
    def test_initial_no_focus(self, manager):
        assert manager.focused_panel is None

    def test_initial_empty(self, manager):
        assert manager.panel_count == 0


class TestFocusManagerRegister:
    def test_register_panel(self, manager, panels):
        manager.register_panel(panels[0])
        assert manager.panel_count == 1

    def test_register_duplicate_ignored(self, manager, panels):
        manager.register_panel(panels[0])
        manager.register_panel(panels[0])
        assert manager.panel_count == 1

    def test_unregister_panel(self, manager, panels):
        manager.register_panel(panels[0])
        manager.unregister_panel(panels[0])
        assert manager.panel_count == 0


class TestFocusManagerSetFocus:
    def test_set_focus(self, manager, panels):
        manager.register_panel(panels[0])
        manager.set_focus(panels[0])
        assert manager.focused_panel is panels[0]

    def test_set_focus_unregistered_ignored(self, manager, panels):
        manager.set_focus(panels[0])
        assert manager.focused_panel is None

    def test_focus_signal(self, manager, panels):
        received = []
        manager.focus_changed.connect(received.append)
        manager.register_panel(panels[0])
        manager.set_focus(panels[0])
        assert panels[0] in received


class TestFocusManagerClear:
    def test_clear_focus(self, manager, panels):
        manager.register_panel(panels[0])
        manager.set_focus(panels[0])
        manager.clear_focus()
        assert manager.focused_panel is None


class TestFocusManagerCycle:
    def test_focus_next_from_none(self, manager, panels):
        for p in panels:
            manager.register_panel(p)
        manager.focus_next()
        assert manager.focused_panel is panels[0]

    def test_focus_next_cycles(self, manager, panels):
        for p in panels:
            manager.register_panel(p)
        manager.set_focus(panels[0])
        manager.focus_next()
        assert manager.focused_panel is panels[1]

    def test_focus_next_wraps(self, manager, panels):
        for p in panels:
            manager.register_panel(p)
        manager.set_focus(panels[2])
        manager.focus_next()
        assert manager.focused_panel is panels[0]


class TestFocusManagerUnregister:
    def test_unregister_focused_clears(self, manager, panels):
        manager.register_panel(panels[0])
        manager.set_focus(panels[0])
        manager.unregister_panel(panels[0])
        assert manager.focused_panel is None
