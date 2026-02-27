import numpy as np
import time

def main():
    print("Starting interaction discovery script...")
    
    # Generate a real trace (e.g. sine wave)
    t = np.linspace(0, 10, 1000)
    real_trace = np.sin(2 * np.pi * t)
    
    # Generate a complex trace
    complex_trace = np.exp(1j * 2 * np.pi * t) + 0.1 * (np.random.randn(1000) + 1j * np.random.randn(1000))
    
    # Another real trace for overlay
    real_trace_2 = np.cos(2 * np.pi * t)

    print("Add these to watch list and interact with them:")
    print(" - real_trace")
    print(" - complex_trace")
    print(" - real_trace_2")
    
    while True:
        # Just update slightly to keep things "alive" if needed, or just sleep
        real_trace = np.sin(2 * np.pi * t + time.time())
        complex_trace = np.exp(1j * 2 * np.pi * t + time.time()) + 0.1 * (np.random.randn(1000) + 1j * np.random.randn(1000))
        real_trace_2 = np.cos(2 * np.pi * t + time.time())
        time.sleep(0.1)

if __name__ == "__main__":
    main()
