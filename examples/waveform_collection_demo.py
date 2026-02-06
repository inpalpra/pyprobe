"""
Example demonstrating waveform collection probing in PyProbe.

Run with: python -m pyprobe examples/waveform_collection_demo.py

Then probe the 'wfms' variable to see multiple waveforms with different time bases.
"""

import numpy as np
import time


class Waveform:
    """Simple waveform container with t0, dt, x."""
    def __init__(self, t0: float, dt: float, x):
        self.t0 = t0
        self.dt = dt
        self.x = np.asarray(x, dtype=float)


if __name__ == "__main__":
    print("=" * 50)
    print("PyProbe Waveform Collection Demo")
    print("=" * 50)
    print()
    print("Probe the 'wfms' variable to see overlapping waveforms.")
    print("Each waveform has different t0, dt, and length.")
    print()

    for frame in range(50):
        # Create waveforms with different time bases
        wfms = [
            Waveform(0.0, 1.0, np.sin(2 * np.pi * 0.5 * np.arange(100) * 0.1 + frame * 0.1)),  # 100 samples, starts at 0
            Waveform(10, 0.2, np.cos(2 * np.pi * 0.3 * np.arange(50) * 0.2 + frame * 0.1)),   # 50 samples, starts at t=2
            Waveform(15, 0.1, np.sin(2 * np.pi * 0.8 * np.arange(200) * 0.05 + frame * 0.1)), # 200 samples, starts at t=1
        ]
        
        time.sleep(0.1)

    print("Demo complete!")
