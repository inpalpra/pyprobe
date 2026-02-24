import pytest
import pyqtgraph as pg
from PyQt6.QtCore import Qt, QPointF
from pyprobe.plots.marker_items import MarkerGlyph, _DraggableScatter
from pyprobe.plots.marker_model import MarkerData, MarkerShape

def test_marker_glyph_moving_signal(qtbot):
    data = MarkerData(id="m0", x=1.0, y=2.0, trace_key="trace1", shape=MarkerShape.DIAMOND, color="#ffffff")
    glyph = MarkerGlyph(data)
    
    signals_received = []
    def on_moving(m_id, x, y):
        signals_received.append((m_id, x, y))
        
    glyph.signaler.marker_moving.connect(on_moving)
    
    # Simulate a drag move
    pos = QPointF(5.0, 10.0)
    glyph._on_drag_move(pos)
    
    assert len(signals_received) == 1
    assert signals_received[0] == ("m0", 5.0, 10.0)
    
    # Check visual pos was updated
    assert glyph.text.pos().x() == 5.0
    assert glyph.text.pos().y() == 10.0
