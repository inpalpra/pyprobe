import pytest
from PyQt6.QtGui import QColor
from pyprobe.gui.probe_panel import ProbePanel
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D
from unittest.mock import MagicMock

def test_view_adjusted_recording(qtbot, qapp):
    anchor = ProbeAnchor(file="test.py", line=1, col=1, symbol="sig")
    panel = ProbePanel(anchor, QColor("red"), DTYPE_ARRAY_1D, trace_id="tr0", window_id="w0")
    qtbot.addWidget(panel)
    
    spy = MagicMock()
    panel.view_adjusted.connect(spy)
    
    # Trigger manual view change signal from ViewBox
    vb = panel._plot._plot_widget.getPlotItem().getViewBox()
    vb.sigRangeChangedManually.emit([True, True])
    
    # Wait for debounce timer
    qapp.processEvents()
    import time
    time.sleep(0.6)
    qapp.processEvents()
    
    assert spy.called
    panel.close()
    panel.deleteLater()
    qapp.processEvents()

def test_view_reset_recording(qtbot, qapp):
    anchor = ProbeAnchor(file="test.py", line=1, col=1, symbol="sig")
    panel = ProbePanel(anchor, QColor("red"), DTYPE_ARRAY_1D, trace_id="tr0", window_id="w0")
    qtbot.addWidget(panel)
    
    spy = MagicMock()
    panel.view_reset_triggered.connect(spy)
    
    panel._on_toolbar_reset()
    
    assert spy.called
    panel.close()
    panel.deleteLater()
    qapp.processEvents()
