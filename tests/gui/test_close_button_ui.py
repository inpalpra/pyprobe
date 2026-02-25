import pytest
from PyQt6.QtWidgets import QPushButton
from pyprobe.gui.panel_container import ProbePanelContainer
from pyprobe.core.anchor import ProbeAnchor

@pytest.fixture
def container(qtbot):
    c = ProbePanelContainer()
    qtbot.addWidget(c)
    return c

def test_close_button_exists(container):
    container.show()
    anchor = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")
    panel = container.create_panel("x", "float", anchor=anchor)
    
    # Find close button in the header
    close_btn = None
    for child in panel.findChildren(QPushButton):
        if child.text() == "×":
            close_btn = child
            break
            
    assert close_btn is not None
    # Use isVisibleTo(panel) because the panel itself might not be fully exposed yet in tests
    assert close_btn.isVisibleTo(panel)
