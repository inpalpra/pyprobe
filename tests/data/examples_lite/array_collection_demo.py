"""
Example demonstrating array collection probing in PyProbe.

Run with: python -m pyprobe examples/array_collection_demo.py

Then probe the 'arrays' variable to see multiple arrays with different sizes.
"""

import numpy as np
import time


if __name__ == "__main__":
    print("=" * 50)
    print("PyProbe Array Collection Demo")
    print("=" * 50)
    print()
    print("Probe the 'arrays' variable to see multiple colored waveforms.")
    print("Each array has a different size.")
    print()

    for frame in range(50):
        # Create arrays with different sizes
        arrays = [
            np.sin(2 * np.pi * 0.05 * np.arange(100) + frame * 0.1),   # 100 samples
            np.cos(2 * np.pi * 0.03 * np.arange(150) + frame * 0.1),   # 150 samples  
            np.sin(2 * np.pi * 0.08 * np.arange(75) + frame * 0.1),    # 75 samples
        ]
        
        time.sleep(0.1)

    print("Demo complete!")
