"""Unit tests for LayoutManager."""

import pytest
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QGridLayout, QLabel

from pyprobe.gui.layout_manager import LayoutManager


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def container(app):
    container = QWidget()
    layout = QGridLayout(container)
    return container


@pytest.fixture
def panels(container):
    p1 = QLabel("Panel 1", container)
    p2 = QLabel("Panel 2", container)
    p3 = QLabel("Panel 3", container)
    layout = container.layout()
    layout.addWidget(p1, 0, 0)
    layout.addWidget(p2, 0, 1)
    layout.addWidget(p3, 1, 0)
    container.show()
    return [p1, p2, p3]


@pytest.fixture
def manager(container):
    return LayoutManager(container)


class TestLayoutManagerInitial:
    def test_initial_no_maximize(self, manager):
        assert not manager.is_maximized

    def test_initial_no_maximized_panel(self, manager):
        assert manager.maximized_panel is None


class TestLayoutManagerMaximize:
    def test_toggle_maximizes(self, manager, panels):
        manager.toggle_maximize(panels[0])
        assert manager.maximized_panel is panels[0]
        assert manager.is_maximized

    def test_toggle_twice_restores(self, manager, panels):
        manager.toggle_maximize(panels[0])
        manager.toggle_maximize(panels[0])
        assert not manager.is_maximized

    def test_maximize_another_restores_first(self, manager, panels):
        manager.toggle_maximize(panels[0])
        manager.toggle_maximize(panels[1])
        assert manager.maximized_panel is panels[1]


class TestLayoutManagerRestore:
    def test_restore_shows_hidden(self, manager, panels):
        manager.toggle_maximize(panels[0])
        manager.restore()
        # All panels should be visible
        for p in panels:
            assert p.isVisible()


class TestLayoutManagerSignals:
    def test_signal_on_maximize(self, manager, panels):
        received = []
        manager.layout_changed.connect(received.append)
        manager.toggle_maximize(panels[0])
        assert True in received

    def test_signal_on_restore(self, manager, panels):
        received = []
        manager.toggle_maximize(panels[0])
        manager.layout_changed.connect(received.append)
        manager.restore()
        assert False in received
