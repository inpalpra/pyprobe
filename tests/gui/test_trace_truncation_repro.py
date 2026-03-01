import numpy as np
import pytest
from pyprobe.plugins.builtins.waveform import WaveformWidget, WaveformFftMagAngleWidget
from pyprobe.plugins.builtins.complex_plots import downsample as complex_downsample
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D
from PyQt6.QtGui import QColor

@pytest.fixture
def waveform_widget(qtbot):
    widget = WaveformWidget("test", QColor("blue"))
    qtbot.addWidget(widget)
    yield widget
    widget.close()
    widget.deleteLater()

@pytest.fixture
def fft_widget(qtbot):
    widget = WaveformFftMagAngleWidget("test_fft", QColor("green"))
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

def test_fft_lens_downsample_boundaries(fft_widget, qtbot):
    """Test that WaveformFftMagAngleWidget traces reach the last frequency bin."""
    # N=500 -> nfft=8192.
    N = 500
    data = np.random.randn(N)
    
    # Set display points low to force downsampling even for 8192
    fft_widget._phase_display_points = 2000 
    
    # Update data
    fft_widget.update_data(data, DTYPE_ARRAY_1D)
    
    # Process events to let reset_view (singleShot) fire
    qtbot.wait(200)
    
    # Magnitude is in fft_widget._curves[0]
    # Phase is in fft_widget._phase_curves[0]
    mag_x, _ = fft_widget._curves[0].getData()
    phase_x, _ = fft_widget._phase_curves[0].getData()
    
    # Since it's FFT, x-axis is frequencies.
    freqs = fft_widget._t_vector
    
    # Check that the last point in curves matches the last point in freqs
    assert mag_x[-1] == freqs[-1], f"Mag trace doesn't reach last freq: {mag_x[-1]} != {freqs[-1]}"
    assert phase_x[-1] == freqs[-1], f"Phase trace doesn't reach last freq: {phase_x[-1]} != {freqs[-1]}"
