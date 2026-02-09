"""
Regression test script for constellation data verification.

This script stores received_symbols from each iteration and writes them
to a file for comparison with GUI-captured values.

Run with: python -m pyprobe regression/constellation_verify.py --auto-run --auto-quit
"""

import numpy as np
import time
import json
import sys

# Simulation parameters
NUM_SYMBOLS = 100  # Smaller for faster test
NUM_FRAMES = 2

# QAM-16 constellation points
QAM16_CONSTELLATION = np.array([
    -3-3j, -3-1j, -3+1j, -3+3j,
    -1-3j, -1-1j, -1+1j, -1+3j,
    +1-3j, +1-1j, +1+1j, +1+3j,
    +3-3j, +3-1j, +3+1j, +3+3j
]) / np.sqrt(10)  # Normalize power

# Storage for verification
_captured_values = []


def generate_qam_signal(num_symbols: int, snr_db: float) -> tuple:
    """Generate QAM-16 symbols with AWGN noise."""
    # Use fixed seed for reproducibility
    np.random.seed(42 + len(_captured_values))
    
    symbol_indices = np.random.randint(0, 16, num_symbols)
    symbols = QAM16_CONSTELLATION[symbol_indices]

    noise_power = 10 ** (-snr_db / 10)
    noise = np.sqrt(noise_power / 2) * (
        np.random.randn(num_symbols) + 1j * np.random.randn(num_symbols)
    )

    received_symbols = symbols + noise
    signal_i = received_symbols.real
    signal_q = received_symbols.imag

    return received_symbols, signal_i, signal_q


def main():
    """Main processing loop."""
    print("Constellation Verification Test")
    print("=" * 40)
    
    for frame in range(NUM_FRAMES):
        snr_db = 20.0  # Fixed SNR for reproducibility
        
        # Generate QAM signal with noise
        received_symbols, signal_i, signal_q = generate_qam_signal(
            NUM_SYMBOLS, snr_db
        )
        
        # Store the value IMMEDIATELY after assignment for verification
        # This is what the probe at line 60 should capture
        _captured_values.append({
            'frame': frame,
            'mean_real': float(np.mean(received_symbols.real)),
            'mean_imag': float(np.mean(received_symbols.imag)),
            'std_real': float(np.std(received_symbols.real)),
            'std_imag': float(np.std(received_symbols.imag)),
            'first_5_real': [float(x) for x in received_symbols.real[:5]],
            'first_5_imag': [float(x) for x in received_symbols.imag[:5]],
        })
        
        print(f"Frame {frame}: mean=({_captured_values[-1]['mean_real']:.4f}, {_captured_values[-1]['mean_imag']:.4f}j)")
        
        time.sleep(0.05)  # Short delay
    
    # Write expected values to file for test verification
    with open('/tmp/constellation_expected.json', 'w') as f:
        json.dump(_captured_values, f, indent=2)
    
    print()
    print(f"Expected values written to /tmp/constellation_expected.json")
    print("Test complete!")


if __name__ == "__main__":
    main()
