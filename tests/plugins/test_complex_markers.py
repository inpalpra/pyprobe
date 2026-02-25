import pytest
import time
import numpy as np
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QPointF
from pyprobe.plugins.builtins.complex_plots import (
    ComplexRIWidget, ComplexMAWidget, ComplexFftMagAngleWidget, SingleCurveWidget
)
from pyprobe.core.data_classifier import DTYPE_ARRAY_COMPLEX

# ... (rest of imports and tests) ...

def test_complex_single_curve_continuous_snapping(qtbot):
    """
    Verify continuous snapping for SingleCurveWidget.
    """
    widget = SingleCurveWidget("test_single", QColor("#ffffff"), "Log Mag (dB)")
    qtbot.addWidget(widget)
    
    # 10 points: y = x
    data = np.arange(10, dtype=float)
    widget.set_data(data, "info")
    
    widget._marker_store.add_marker("Log Mag (dB)", 5.0, 5.0)
    m_id = widget._marker_store.get_markers()[0].id
    glyph = widget._marker_glyphs[m_id]
    
    glyph._on_drag_move(QPointF(6.1, -10.0))
    assert glyph.text.pos().x() == pytest.approx(6.1, abs=0.01)
    assert glyph.text.pos().y() == pytest.approx(6.1, abs=0.01)

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
    
    # Desired behavior: Visual position is snapped to the nearest point on trace (6.1, 6.1)
    assert glyph.text.pos().x() == pytest.approx(6.1, abs=0.01)
    assert glyph.text.pos().y() == pytest.approx(6.1, abs=0.01)

def test_complex_ma_continuous_snapping(qtbot, monkeypatch):
    """
    Verify continuous snapping for Mag & Phase widget (dual axis).
    """
    widget = ComplexMAWidget("test_ma", QColor("#ffffff"))
    qtbot.addWidget(widget)
    
    # Mock time.perf_counter to avoid throttling
    current_time = [0.0]
    monkeypatch.setattr(time, "perf_counter", lambda: current_time[0])
    
    # 10 points: Mag = [0..9] dB, Phase = [0..3] rad
    mag_db = np.arange(10, dtype=float)
    phase = np.linspace(0, 3, 10)
    z = 10**(mag_db/20.0) * np.exp(1j * phase)
    widget.update_data(z)
    
    # 1. Test Log Mag (Primary Axis)
    widget._marker_store.add_marker("Log Mag", 5.0, 5.0)
    m_id_mag = widget._marker_store.get_markers()[0].id
    glyph_mag = widget._marker_glyphs[m_id_mag]
    
    current_time[0] += 0.1
    glyph_mag._on_drag_move(QPointF(6.1, 20.0)) # Drag far away in Y
    assert glyph_mag.text.pos().x() == pytest.approx(6.1, abs=0.01)
    assert glyph_mag.text.pos().y() == pytest.approx(6.1, abs=0.01)
    
    # 2. Test Phase (Secondary Axis)
    widget._marker_store.add_marker("Phase", 3.0, phase[3])
    m_id_phase = widget._marker_store.get_markers()[1].id
    glyph_phase = widget._marker_glyphs[m_id_phase]
    
    current_time[0] += 0.1
    # Drag to x=4.1. Expected y is interp(4.1, [0..9], phase)
    expected_y = np.interp(4.1, np.arange(10), phase)
    glyph_phase._on_drag_move(QPointF(4.1, -10.0)) # Drag far away in Y
    assert glyph_phase.text.pos().x() == pytest.approx(4.1, abs=0.01)
    assert glyph_phase.text.pos().y() == pytest.approx(expected_y, abs=0.01)

def test_complex_fft_continuous_snapping(qtbot):
    """
    Verify continuous snapping for FFT Mag & Angle widget.
    """
    widget = ComplexFftMagAngleWidget("test_fft", QColor("#ffffff"))
    qtbot.addWidget(widget)
    
    # Use 100 points of a complex sine wave to get some FFT peaks
    t = np.linspace(0, 1, 100)
    z = np.exp(1j * 2 * np.pi * 10 * t) # 10 Hz
    widget.set_data(z, "info")
    
    # FFT freqs and data are now populated
    # Find a point on the mag curve
    mag_curve, _ = widget._series_curves["FFT Mag (dB)"]
    x_data, y_data = mag_curve.getData()
    
    target_idx = len(x_data) // 2
    target_x = x_data[target_idx]
    target_y = y_data[target_idx]
    
    widget._marker_store.add_marker("FFT Mag (dB)", target_x, target_y)
    m_id = widget._marker_store.get_markers()[0].id
    glyph = widget._marker_glyphs[m_id]
    
    # Drag slightly away
    test_x = target_x + (x_data[target_idx+1] - x_data[target_idx]) * 0.1
    glyph._on_drag_move(QPointF(test_x, target_y + 10.0))
    
    # It should snap back to the curve
    # Since it's interpolated, it should be very close to the trace
    assert glyph.text.pos().x() == pytest.approx(test_x, abs=0.01)
    # y should be interpolated between target_y and y_data[target_idx+1]
    expected_y = np.interp(test_x, x_data, y_data)
    assert glyph.text.pos().y() == pytest.approx(expected_y, abs=0.01)
