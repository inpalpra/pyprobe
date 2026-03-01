import numpy as np
import pytest
from pyprobe.plugins.builtins.waveform import WaveformWidget
from pyprobe.plugins.builtins.complex_plots import downsample as complex_downsample
from PyQt6.QtGui import QColor

@pytest.fixture
def waveform_widget(qtbot):
    widget = WaveformWidget("test", QColor("blue"))
    qtbot.addWidget(widget)
    yield widget
    widget.close()
    widget.deleteLater()

def test_waveform_downsample_boundaries(waveform_widget):
    """Test that WaveformWidget.downsample covers [0, N-1]."""
    # Use a length that is not a multiple of n_chunks
    # Default n_points = 5000 -> n_chunks = 2500
    # 8192 / 2500 = 3.27... -> chunk_size = 3
    # n_chunks * chunk_size = 2500 * 3 = 7500. 
    # Truncates 8192 - 7500 = 692 samples.
    N = 8192
    data = np.arange(N, dtype=float)
    
    x, y = waveform_widget.downsample(data)
    
    # If it truncates, the last x index will be < N-1
    assert x[0] == 0, f"Expected first index 0, got {x[0]}"
    assert x[-1] == N - 1, f"Expected last index {N-1}, got {x[-1]}"

def test_complex_downsample_boundaries():
    """Test that complex_plots.downsample covers [0, N-1]."""
    N = 8192
    data = np.arange(N, dtype=float)
    
    # complex_downsample uses n_points // 2 chunks. Default n_points=5000 -> 2500 chunks.
    x, y = complex_downsample(data)
    
    assert x[0] == 0, f"Expected first index 0, got {x[0]}"
    assert x[-1] == N - 1, f"Expected last index {N-1}, got {x[-1]}"

def test_waveform_downsample_prime(waveform_widget):
    N = 10007
    data = np.arange(N, dtype=float)
    x, y = waveform_widget.downsample(data)
    assert x[-1] == N - 1, f"Expected last index {N-1}, got {x[-1]}"

def test_waveform_downsample_pow2_plus_1(waveform_widget):
    N = 8193
    data = np.arange(N, dtype=float)
    x, y = waveform_widget.downsample(data)
    assert x[-1] == N - 1, f"Expected last index {N-1}, got {x[-1]}"
