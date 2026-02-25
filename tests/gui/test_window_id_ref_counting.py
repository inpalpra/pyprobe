import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from pyprobe.gui.panel_container import ProbePanelContainer
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.trace_reference_manager import TraceReferenceManager

@pytest.fixture
def container(qtbot):
    # Reset singleton for tests
    TraceReferenceManager._instance = None
    c = ProbePanelContainer()
    qtbot.addWidget(c)
    return c

def test_window_id_and_ref_counting(container):
    # Mock the singleton instance
    ref_manager = TraceReferenceManager.instance()
    ref_manager.add_reference = MagicMock()
    ref_manager.cleanup_window = MagicMock()
    
    # Create first panel
    anchor1 = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")
    panel1 = container.create_panel("x", "float", anchor=anchor1, trace_id="tr0")
    
    # Assert it has a window_id and it's w0
    assert panel1.window_id == "w0"
    
    # Verify add_reference was called
    ref_manager.add_reference.assert_called_with("tr0", "w0")
    
    # Remove first panel
    container.remove_panel(panel=panel1)
    
    # Verify cleanup_window was called
    ref_manager.cleanup_window.assert_called_with("w0")
