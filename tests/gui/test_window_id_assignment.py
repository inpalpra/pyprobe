import pytest
from PyQt6.QtWidgets import QApplication
from pyprobe.gui.panel_container import ProbePanelContainer
from pyprobe.core.anchor import ProbeAnchor

@pytest.fixture
def container(qtbot):
    c = ProbePanelContainer()
    qtbot.addWidget(c)
    return c

def test_window_id_assignment(container):
    # Create first panel
    anchor1 = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")
    panel1 = container.create_panel("x", "float", anchor=anchor1)
    
    # Assert it has a window_id and it's w0
    assert hasattr(panel1, "window_id")
    assert panel1.window_id == "w0"
    
    # Create second panel
    anchor2 = ProbeAnchor(file="test.py", line=20, col=0, symbol="y")
    panel2 = container.create_panel("y", "float", anchor=anchor2)
    
    # Assert it has w1
    assert panel2.window_id == "w1"
    
    # Remove first panel and create another
    container.remove_panel(panel=panel1)
    
    anchor3 = ProbeAnchor(file="test.py", line=30, col=0, symbol="z")
    panel3 = container.create_panel("z", "float", anchor=anchor3)
    
    # Assert it reuses w0 (since it was released)
    assert panel3.window_id == "w0"
