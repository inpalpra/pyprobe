import sys
import numpy as np
import time

def main():
    import pyprobe
    
    probe = pyprobe.Probe("test_sig")
    data = np.exp(2j * np.pi * 10 * np.linspace(0, 1, 500))
    probe.feed(data)
    time.sleep(1)

if __name__ == "__main__":
    main()
