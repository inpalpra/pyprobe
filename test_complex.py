import numpy as np
import pyprobe
import time

complex_sig = np.exp(2j * np.pi * 10 * np.linspace(0, 1, 500))

probe = pyprobe.Probe("test_sig")
probe.feed(complex_sig)
time.sleep(1)
