import numpy as np

def main():
    print("Starting interaction discovery script...")
    
    # Generate a real trace
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
    
    print("Script finished. The UI will remain open if run with PyProbe.")

if __name__ == "__main__":
    main()
