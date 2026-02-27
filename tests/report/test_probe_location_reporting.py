import pytest
from unittest.mock import MagicMock
from pyprobe.gui.probe_controller import ProbeController
from pyprobe.core.anchor import ProbeAnchor

def test_probe_trace_entries_includes_line_column():
    # Mock dependencies
    registry = MagicMock()
    container = MagicMock()
    code_viewer = MagicMock()
    gutter = MagicMock()
    
    controller = ProbeController(
        registry, container, code_viewer, gutter,
        get_ipc=lambda: None, get_is_running=lambda: False
    )
    
    anchor = ProbeAnchor(file="test.py", line=42, col=7, symbol="sig")
    controller._probe_metadata[anchor] = {
        'shape': (100,),
        'dtype': 'float64'
    }
    
    entries = controller.probe_trace_entries()
    assert len(entries) == 1
    entry = entries[0]
    
    assert entry.symbol == "sig"
    assert entry.file == "test.py"
    assert entry.line == 42
    assert entry.column == 7
    assert entry.shape == (100,)
    assert entry.dtype == "float64"
