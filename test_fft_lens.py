import sys
import numpy as np
import pyprobe

def generate_test_data():
    t = np.linspace(0, 1, 1000, endpoint=False)
    # create a complex signal with 2 frequencies: 10Hz and 50Hz
    # adding some noise
    complex_sig = np.exp(2j * np.pi * 10 * t) + 0.5 * np.exp(-2j * np.pi * 50 * t) + 0.1 * (np.random.randn(len(t)) + 1j * np.random.randn(len(t)))
    
    # create a real waveform with 20Hz
    real_sig = np.sin(2 * np.pi * 20 * t) + 0.05 * np.random.randn(len(t))
    
    return complex_sig, real_sig

if __name__ == "__main__":
    complex_sig, real_sig = generate_test_data()
    
    import pyprobe
    # In PyProbe, usually we use pyprobe.Probe(name) and then feed() or update()
    p_comp = pyprobe.Probe("complex_signal")
    p_comp.feed(complex_sig)
    
    p_real = pyprobe.Probe("real_signal")
    p_real.feed(real_sig)
    
    print("Sent test data to PyProbe.")
