import pytest
import numpy as np
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QPointF
from pyprobe.plugins.builtins.complex_plots import ComplexRIWidget
from pyprobe.core.data_classifier import DTYPE_ARRAY_COMPLEX

def test_complex_continuous_snapping(qtbot):
    """
    Verify that dragging a marker in a Complex widget snaps continuously to the trace.
    """
    widget = ComplexRIWidget("test_complex", QColor("#ffffff"))
    qtbot.addWidget(widget)
    
    # 10 points: Real = [0..9], Imag = [0..9]
    data = np.arange(10, dtype=complex) + 1j * np.arange(10, dtype=complex)
    widget.update_data(data)
    
    # Add a marker on the "Real" trace at x=5, y=5
    widget._marker_store.add_marker("Real", 5.0, 5.0)
    
    m_id = widget._marker_store.get_markers()[0].id
    glyph = widget._marker_glyphs[m_id]
    
    # Simulate a drag move to x=6.1, y=9.0 (far from the trace y=x)
    glyph._on_drag_move(QPointF(6.1, 9.0))
    
    # Desired behavior: Visual position is snapped to the nearest point on trace (6.0, 6.0)
    assert glyph.text.pos().x() == pytest.approx(6.0, abs=0.1)
    assert glyph.text.pos().y() == pytest.approx(6.0, abs=0.1)
