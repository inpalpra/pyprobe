import pytest
import numpy as np
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QPointF
from pyprobe.plugins.builtins.waveform import WaveformWidget
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D

def test_waveform_continuous_snapping(qtbot):
    widget = WaveformWidget("test_var", QColor("#ffffff"))
    qtbot.addWidget(widget)
    
    # 10 points: y = x
    data = np.arange(10, dtype=float)
    widget.update_data(data, DTYPE_ARRAY_1D)
    
    # Add a marker
    widget._marker_store.add_marker(0, 5.0, 5.0)
    
    m_id = widget._marker_store.get_markers()[0].id
    glyph = widget._marker_glyphs[m_id]
    
    glyph._on_drag_move(QPointF(6.1, 9.0))
    
    assert glyph.text.pos().x() == pytest.approx(6.0, abs=0.2)
    assert glyph.text.pos().y() == pytest.approx(6.0, abs=0.2)
    
    assert "X=6" in widget._marker_overlay.labels[m_id].text()
    assert "Y=6" in widget._marker_overlay.labels[m_id].text()

def test_waveform_continuous_snapping_throttling(qtbot, monkeypatch):
    import time
    widget = WaveformWidget("test_var", QColor("#ffffff"))
    qtbot.addWidget(widget)
    
    data = np.arange(10, dtype=float)
    widget.update_data(data, DTYPE_ARRAY_1D)
    
    widget._marker_store.add_marker(0, 5.0, 5.0)
    m_id = widget._marker_store.get_markers()[0].id
    glyph = widget._marker_glyphs[m_id]
    
    # Mock time.perf_counter
    current_time = [0.0]
    def mock_time():
        return current_time[0]
    monkeypatch.setattr(time, "perf_counter", mock_time)
    
    # 1. Normal snap at t=0.0
    glyph._on_drag_move(QPointF(6.1, 9.0))
    assert glyph.text.pos().x() == pytest.approx(6.0, abs=0.2)
    
    # 2. Try to snap immediately (throttled)
    current_time[0] = 0.005 # 5ms later
    glyph._on_drag_move(QPointF(7.1, 9.0))
    # Should not be snapped to 7.0, it should be exactly 7.1
    assert glyph.text.pos().x() == pytest.approx(7.1, abs=0.01)
    
    # 3. Normal snap at t=0.02 (> 16ms)
    current_time[0] = 0.020 # 20ms later
    glyph._on_drag_move(QPointF(8.1, 9.0))
    assert glyph.text.pos().x() == pytest.approx(8.0, abs=0.2)
def test_waveform_continuous_snapping_interpolation(qtbot):
    widget = WaveformWidget("test_var", QColor("#ffffff"))
    qtbot.addWidget(widget)
    
    # 10 points: y = x * 2  => (0,0), (1,2), (2,4)
    data = np.arange(10, dtype=float) * 2.0
    widget.update_data(data, DTYPE_ARRAY_1D)
    
    widget._marker_store.add_marker(0, 1.0, 2.0)
    m_id = widget._marker_store.get_markers()[0].id
    glyph = widget._marker_glyphs[m_id]
    
    # Drag to x=1.5. It should interpolate between (1, 2) and (2, 4)
    # y should be 3.0
    glyph._on_drag_move(QPointF(1.5, 9.0))
    
    # Visual position
    assert glyph.text.pos().x() == pytest.approx(1.5, abs=0.01)
    assert glyph.text.pos().y() == pytest.approx(3.0, abs=0.01)
