
import pytest
import numpy as np
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.plugins.builtins.complex_plots import ComplexRIWidget, ComplexMAWidget
from pyprobe.plugins.builtins.waveform import WaveformWidget
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D, DTYPE_ARRAY_COMPLEX

@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])

def get_legend_labels(widget):
    """Helper to extract text labels from a widget's legend."""
    if not hasattr(widget, '_legend') or not widget._legend:
        return []
    legend = widget._legend
    return [label.text if hasattr(label, 'text') else str(label) for _, label in legend.items]

def test_complex_ri_legend_format(qapp, qtbot):
    anchor = ProbeAnchor(file="test.py", line=10, col=5, symbol="sig")
    widget = ComplexRIWidget("sig", QColor("cyan"), trace_id="tr1")
    qtbot.addWidget(widget)
    
    labels = get_legend_labels(widget)
    # Format: <trace_id>: <symbol> (<component>)
    assert "tr1: sig (real)" in labels
    assert "tr1: sig (imag)" in labels

def test_waveform_fft_legend_format(qapp, qtbot):
    anchor = ProbeAnchor(file="test.py", line=10, col=5, symbol="sig")
    from pyprobe.plugins.builtins.waveform import WaveformFftMagAngleWidget
    widget = WaveformFftMagAngleWidget("sig", QColor("cyan"), trace_id="tr2")
    qtbot.addWidget(widget)
    
    labels = get_legend_labels(widget)
    # WaveformFftMagAngleWidget adds (fft_mag_db) and potentially (fft_angle_deg)
    assert "tr2: sig (fft_mag_db)" in labels
    
    # Trigger phase curve creation
    widget.update_data(np.array([1, 2, 3]), DTYPE_ARRAY_1D)
    labels = get_legend_labels(widget)
    assert "tr2: sig (fft_angle_deg)" in labels

def test_complex_ma_legend_format(qapp, qtbot):
    widget = ComplexMAWidget("sig", QColor("cyan"), trace_id="tr4")
    qtbot.addWidget(widget)
    
    labels = get_legend_labels(widget)
    assert "tr4: sig (mag_db)" in labels
    assert "tr4: sig (phase_rad)" in labels

def test_waveform_legend_format(qapp, qtbot):
    widget = WaveformWidget("sig", QColor("cyan"), trace_id="tr5")
    qtbot.addWidget(widget)
    
    labels = get_legend_labels(widget)
    # Single trace labels don't always have parens if not multi-component, 
    # but should still have trace_id prefix
    assert "tr5: sig" in labels
