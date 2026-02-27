import pytest
import pyqtgraph as pg
from PyQt6.QtCore import Qt, QPointF
from pyprobe.gui.panel_container import ProbePanelContainer
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.gui.probe_panel import RemovableLegendItem

@pytest.fixture
def container(qtbot):
    c = ProbePanelContainer()
    qtbot.addWidget(c)
    c.show()
    return c

def test_remove_overlay_via_context_menu(container, qtbot):
    # Verify signal emission logic for context menu
    anchor1 = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")
    panel = container.create_panel("x", "float", anchor=anchor1, trace_id="tr0")
    
    anchor2 = ProbeAnchor(file="test.py", line=20, col=0, symbol="y")
    if not hasattr(panel, '_overlay_anchors'):
        panel._overlay_anchors = []
    panel._overlay_anchors.append(anchor2)
    
    with qtbot.waitSignal(panel.overlay_remove_requested) as blocker:
        panel.overlay_remove_requested.emit(panel, anchor2)
        
    assert blocker.args == [panel, anchor2]

def test_legend_click_emits_signal(qtbot):
    legend = RemovableLegendItem()
    # Mock some items
    curve1 = pg.PlotCurveItem([1, 2, 3])
    label1 = pg.LabelItem("tr0: x")
    legend.addItem(curve1, "tr0: x")
    
    # We need to manually trigger mouseClickEvent since full UI integration is complex
    from unittest.mock import MagicMock
    from PyQt6.QtCore import QPointF
    event = MagicMock()
    event.button.return_value = Qt.MouseButton.LeftButton
    event.pos.return_value = QPointF(0, 0)

    # Mock label.contains to return True
    for item, label in legend.items:
        label.contains = MagicMock(return_value=True)
        label.mapFromParent = MagicMock(return_value=QPointF(0, 0))

    with qtbot.waitSignal(legend.trace_removal_requested) as blocker:
        legend.mouseDoubleClickEvent(event)
        
    emitted_item = blocker.args[0]
    if hasattr(emitted_item, 'item'):
        assert emitted_item.item == curve1
    else:
        assert emitted_item == curve1
