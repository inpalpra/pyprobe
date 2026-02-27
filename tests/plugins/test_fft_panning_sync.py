
import pytest
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor
from pyprobe.plugins.builtins.waveform import WaveformFftMagAngleWidget
from pyprobe.plugins.builtins.complex_plots import ComplexMAWidget

@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])

def test_waveform_fft_panning_sync(qapp, qtbot):
    widget = WaveformFftMagAngleWidget("test", QColor("cyan"))
    qtbot.addWidget(widget)
    
    t = np.linspace(0, 1, 100)
    sig = np.sin(2 * np.pi * 10 * t)
    widget.update_data(sig, "array_1d")
    widget._p1.vb.autoRange()
    
    widget._axis_controller.set_pinned('y', False)
    widget._p1.vb.setYRange(-50, 50, padding=0)
    
    mag_base = widget._p1.vb.viewRange()[1]
    phase_base = widget._p2.viewRange()[1]
    mag_h = mag_base[1] - mag_base[0]
    phase_h = phase_base[1] - phase_base[0]
    
    widget._axis_controller.set_pinned('y', True)
    widget._p1.vb.setYRange(mag_base[0] + 10, mag_base[1] + 10, padding=0)
    
    mag_new = widget._p1.vb.viewRange()[1]
    phase_new = widget._p2.viewRange()[1]
    
    dy_mag = mag_new[0] - mag_base[0]
    dy_phase = phase_new[0] - phase_base[0]
    
    assert pytest.approx(dy_phase / phase_h) == dy_mag / mag_h

def test_complex_ma_panning_sync(qapp, qtbot):
    widget = ComplexMAWidget("test", QColor("cyan"))
    qtbot.addWidget(widget)
    
    sig = np.exp(2j * np.pi * 10 * np.linspace(0, 1, 100))
    widget.update_data(sig)
    
    # Explicitly set initial phase range for stability
    widget._p2.setYRange(-np.pi, np.pi, padding=0)
    
    widget._axis_controller.set_pinned('y', False)
    widget._p1.vb.setYRange(-50, 50, padding=0)
    
    mag_base = widget._p1.vb.viewRange()[1]
    phase_base = widget._p2.viewRange()[1]
    mag_h = mag_base[1] - mag_base[0]
    phase_h = phase_base[1] - phase_base[0]
    
    widget._axis_controller.set_pinned('y', True)
    widget._p1.vb.setYRange(mag_base[0] + 10, mag_base[1] + 10, padding=0)
    
    mag_new = widget._p1.vb.viewRange()[1]
    phase_new = widget._p2.viewRange()[1]
    
    dy_mag = mag_new[0] - mag_base[0]
    dy_phase = phase_new[0] - phase_base[0]
    
    assert pytest.approx(dy_phase / phase_h) == dy_mag / mag_h
