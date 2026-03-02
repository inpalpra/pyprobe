"""Integration tests for 3-stage maximization cycle in MainWindow."""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from pyprobe.gui.main_window import MainWindow
from pyprobe.gui.layout_manager import MaximizeState
import os

@pytest.fixture
def window(qtbot):
    win = MainWindow()
    win.show()
    qtbot.addWidget(win)
    return win

def test_maximize_cycle_ui_visibility(window, qtbot):
    # Setup: add a probe so we have something to maximize
    # Mocking code viewer to provide a variable
    from pyprobe.core.anchor import ProbeAnchor
    anchor = ProbeAnchor(file="test.py", line=10, col=5, symbol="x")
    window._on_probe_requested(anchor)
    
    panel = window._probe_container.get_all_panels()[0]
    lm = window._probe_container.layout_manager
    
    # Initial state
    assert lm.state == MaximizeState.NORMAL
    assert window._tree_pane.isVisible()
    assert window._watch_pane.isVisible()
    assert window._code_container.isVisible()
    assert window._control_bar.isVisible()
    
    # Stage 1: NORMAL -> CONTAINER
    # Trigger 'M' key on the panel
    qtbot.keyClick(panel, Qt.Key.Key_M)
    assert lm.state == MaximizeState.CONTAINER
    # Sidebars should still be visible in this state
    assert window._tree_pane.isVisible()
    assert window._watch_pane.isVisible()
    assert window._code_container.isVisible()
    assert window._control_bar.isVisible()
    
    # Stage 2: CONTAINER -> FULL
    qtbot.keyClick(panel, Qt.Key.Key_M)
    assert lm.state == MaximizeState.FULL
    # All non-graph widgets should be hidden
    assert not window._tree_pane.isVisible()
    assert not window._watch_pane.isVisible()
    assert not window._code_container.isVisible()
    assert not window._control_bar.isVisible()
    # Status bar should show restoration tip
    assert "Press 'M' to restore" in window._status_bar.currentMessage()
    
    # Stage 3: FULL -> NORMAL
    qtbot.keyClick(panel, Qt.Key.Key_M)
    assert lm.state == MaximizeState.NORMAL
    # All widgets should be restored
    assert window._tree_pane.isVisible()
    assert window._watch_pane.isVisible()
    assert window._code_container.isVisible()
    assert window._control_bar.isVisible()

def test_maximize_restores_previous_visibility(window, qtbot):
    # Setup: hide the watch pane manually in Stage 1
    window._watch_pane.hide()
    assert not window._watch_pane.isVisible()
    
    from pyprobe.core.anchor import ProbeAnchor
    anchor = ProbeAnchor(file="test.py", line=10, col=5, symbol="x")
    window._on_probe_requested(anchor)
    panel = window._probe_container.get_all_panels()[0]
    
    # Stage 1: CONTAINER
    qtbot.keyClick(panel, Qt.Key.Key_M)
    # Stage 2: FULL
    qtbot.keyClick(panel, Qt.Key.Key_M)
    assert not window._watch_pane.isVisible()
    
    # Stage 3: NORMAL
    qtbot.keyClick(panel, Qt.Key.Key_M)
    # Watch pane should still be hidden (restored to its state before FULL)
    assert not window._watch_pane.isVisible()
    assert window._code_container.isVisible()

def test_status_bar_coordinates_visible_in_full(window, qtbot):
    from pyprobe.core.anchor import ProbeAnchor
    anchor = ProbeAnchor(file="test.py", line=10, col=5, symbol="x")
    window._on_probe_requested(anchor)
    panel = window._probe_container.get_all_panels()[0]
    
    # Go to FULL mode
    qtbot.keyClick(panel, Qt.Key.Key_M)
    qtbot.keyClick(panel, Qt.Key.Key_M)
    assert window._probe_container.layout_manager.state == MaximizeState.FULL
    
    # Simulate coordinate update
    window._on_probe_status_message("X: 1.23, Y: 4.56")
    assert window._coord_label.text() == "X: 1.23, Y: 4.56"
    assert window._coord_label.isVisible()
