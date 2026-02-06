"""
Example demonstrating Waveform object probing in PyProbe.

Run with: python -m pyprobe examples/waveform_demo.py

Then probe the 'wfm' variable to see the waveform plot with proper time axis.
"""

import numpy as np
import time


class Waveform:
    """
    Simple container for a sampled waveform.

    Parameters
    ----------
    t0 : float
        Start time.
    dt : float
        Sampling interval.
    x : 1-D array-like
        Amplitude values.
    """
    def __init__(self, t0: float, dt: float, x):
        self.t0 = t0
        self.dt = dt
        self.x = np.asarray(x, dtype=float)

    @property
    def t(self):
        """Time vector corresponding to the samples."""
        return self.t0 + np.arange(len(self.x)) * self.dt


# ----------------------------------------------------------------------
# Main loop - 0.5 Hz sine wave with varying frequency
if __name__ == "__main__":
    print("=" * 50)
    print("PyProbe Waveform Demo")
    print("=" * 50)
    print()
    print("Probe the 'wfm' variable to see the waveform plot.")
    print()

    t0 = 0.0                 # start time
    dt = 1.0                 # sampling interval
    N  = 100                 # number of samples

    for frame in range(50):
        # Vary frequency over time
        freq = 0.3 + 0.2 * np.sin(2 * np.pi * frame / 25)
        x = np.sin(2 * np.pi * freq * (np.arange(N) * dt))

        wfm = Waveform(t0, dt, x)   # create object (PROBE THIS!)

        time.sleep(0.1)  # 100ms per frame

    print("Demo complete!")
