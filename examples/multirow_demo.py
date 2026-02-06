"""
Example demonstrating multi-row 2D array probing in PyProbe.

Run with: python -m pyprobe examples/multirow_demo.py

Then probe the 'data' variable to see multiple colored waveforms.
"""

import numpy as np
import time


if __name__ == "__main__":
    print("=" * 50)
    print("PyProbe Multi-Row Demo")
    print("=" * 50)
    print()
    print("Probe the 'data' variable to see multiple colored waveforms.")
    print("Click legend items to toggle row visibility.")
    print()

    for frame in range(50):
        # 5 rows of sine waves with different phases
        t = np.linspace(0, 2 * np.pi, 100)
        data = np.vstack([
            np.sin(t + frame * 0.1 + i * 0.3)
            for i in range(5)
        ])
        
        time.sleep(0.1)

    print("Demo complete!")
