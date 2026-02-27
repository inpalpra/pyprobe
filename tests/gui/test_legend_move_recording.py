import pytest
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor
from pyprobe.gui.probe_panel import ProbePanel, RemovableLegendItem
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D
from unittest.mock import MagicMock

def test_legend_drag_emits_signal(qapp):
    anchor = ProbeAnchor(file="test.py", line=1, col=1, symbol="sig")
    panel = ProbePanel(anchor, QColor("red"), DTYPE_ARRAY_1D, trace_id="tr0", window_id="w0")
    
    legend = panel._plot._legend
    assert isinstance(legend, RemovableLegendItem)
    
    spy = MagicMock()
    legend.legend_moved.connect(spy)
    
    # Simulate a drag event
    mock_event = MagicMock()
    mock_event.button.return_value = Qt.MouseButton.LeftButton
    mock_event.isFinish.return_value = True
    mock_event.pos.return_value = QPointF(10, 10)
    mock_event.lastPos.return_value = QPointF(0, 0)
    
    legend.mouseDragEvent(mock_event)
    
    assert spy.called

def test_panel_forwards_legend_moved(qapp):
    anchor = ProbeAnchor(file="test.py", line=1, col=1, symbol="sig")
    panel = ProbePanel(anchor, QColor("red"), DTYPE_ARRAY_1D, trace_id="tr0", window_id="w0")
    
    spy = MagicMock()
    panel.legend_moved.connect(spy)
    
    panel._plot._legend.legend_moved.emit()
    
    assert spy.called
