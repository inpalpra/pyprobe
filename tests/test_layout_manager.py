"""Unit tests for LayoutManager."""

import pytest
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QGridLayout, QLabel

from pyprobe.gui.layout_manager import LayoutManager, MaximizeState


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
    # LayoutManager needs container._panels dict to find panels
    container._panels = {"a0": [p1], "a1": [p2], "a2": [p3]}
    return [p1, p2, p3]


@pytest.fixture
def manager(container):
    return LayoutManager(container)


class TestLayoutManagerInitial:
    def test_initial_no_maximize(self, manager):
        assert not manager.is_maximized
        assert manager.state == MaximizeState.NORMAL

    def test_initial_no_maximized_panel(self, manager):
        assert manager.maximized_panel is None


class TestLayoutManager3StageCycle:
    def test_cycle_transitions(self, manager, panels):
        # Stage 1: NORMAL -> CONTAINER
        manager.toggle_maximize(panels[0])
        assert manager.state == MaximizeState.CONTAINER
        assert manager.maximized_panel is panels[0]
        
        # Stage 2: CONTAINER -> FULL
        manager.toggle_maximize(panels[0])
        assert manager.state == MaximizeState.FULL
        assert manager.maximized_panel is panels[0]
        
        # Stage 3: FULL -> NORMAL
        manager.toggle_maximize(panels[0])
        assert manager.state == MaximizeState.NORMAL
        assert manager.maximized_panel is None

    def test_full_maximize_signal(self, manager, panels):
        received = []
        manager.full_maximize_toggled.connect(received.append)
        
        # NORMAL -> CONTAINER (no full signal)
        manager.toggle_maximize(panels[0])
        assert len(received) == 0
        
        # CONTAINER -> FULL (full signal True)
        manager.toggle_maximize(panels[0])
        assert True in received
        
        # FULL -> NORMAL (full signal False)
        manager.toggle_maximize(panels[0])
        assert False in received

    def test_switch_focus_during_container_maximize(self, manager, panels):
        # NORMAL -> CONTAINER (p0)
        manager.toggle_maximize(panels[0])
        assert manager.maximized_panel is panels[0]
        
        # Press 'M' on p1 while p0 is maximized in container
        # Should switch CONTAINER focus to p1
        manager.toggle_maximize(panels[1])
        assert manager.state == MaximizeState.CONTAINER
        assert manager.maximized_panel is panels[1]

    def test_restore_from_any_state(self, manager, panels):
        # Restore from CONTAINER
        manager.toggle_maximize(panels[0])
        manager.restore()
        assert manager.state == MaximizeState.NORMAL
        
        # Restore from FULL
        manager.toggle_maximize(panels[0])
        manager.toggle_maximize(panels[0])
        assert manager.state == MaximizeState.FULL
        manager.restore()
        assert manager.state == MaximizeState.NORMAL


class TestLayoutManagerSignals:
    def test_signal_on_maximize(self, manager, panels):
        received = []
        manager.layout_changed.connect(received.append)
        manager.toggle_maximize(panels[0])
        assert True in received

    def test_signal_on_restore(self, manager, panels):
        manager.toggle_maximize(panels[0])
        received = []
        manager.layout_changed.connect(received.append)
        manager.restore()
        assert False in received
