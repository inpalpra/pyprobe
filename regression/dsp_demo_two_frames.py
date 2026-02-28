"""
Regression test script for drag-drop overlay verification.

This is a copy of examples/dsp_demo.py with NUM_FRAMES=1 for
single-iteration testing of the overlay functionality.

Run with: python -m pyprobe regression/dsp_demo_single_frame.py --auto-run --auto-quit
"""

import json
import numpy as np
import time

# Simulation parameters
NUM_SYMBOLS = 64
NUM_FRAMES = 2  # Two frames for test

# QAM-16 constellation points
QAM16_CONSTELLATION = np.array([
    -3-3j, -3-1j, -3+1j, -3+3j,
    -1-3j, -1-1j, -1+1j, -1+3j,
    +1-3j, +1-1j, +1+1j, +1+3j,
    +3-3j, +3-1j, +3+1j, +3+3j
]) / np.sqrt(10)  # Normalize power

# Use fixed seed for reproducibility in tests
np.random.seed(42)


def generate_qam_signal(num_symbols: int, snr_db: float) -> tuple:
    """Generate QAM-16 symbols with AWGN noise."""
    # Generate random symbol indices
    symbol_indices = np.random.randint(0, 16, num_symbols)

    # Map to constellation points
    symbols = QAM16_CONSTELLATION[symbol_indices]

    # Add AWGN noise
    noise_power = 10 ** (-snr_db / 10)
    noise = np.sqrt(noise_power / 2) * (
        np.random.randn(num_symbols) + 1j * np.random.randn(num_symbols)
    )

    received_symbols = symbols + noise

    # Extract I and Q components
    signal_i = 0.5*received_symbols.real  # Scale for visibility
    signal_q = 0.5*received_symbols.imag  # Scale for visibility

    return received_symbols, signal_i, signal_q


def main():
    """Main processing loop."""

    # Storage for expected values (for test verification)
    expected_data = []

    for frame in range(NUM_FRAMES):
        # Fixed SNR for reproducibility
        snr_db = 20.0

        # Generate QAM signal with noise
        received_symbols, signal_i, signal_q = generate_qam_signal(
            NUM_SYMBOLS, snr_db
        )

        # Store pre-offset values for test verification
        # (the overlay captures at this point, before the offset)
        pre_offset_real = received_symbols.real.tolist()
        pre_offset_imag = received_symbols.imag.tolist()

        # Offset to make overlay distinguishable
        received_symbols = received_symbols + np.complex128(-1-1j)

        # Store expected values for test verification
        expected_data.append({
            'frame': frame,
            'signal_i': signal_i.tolist(),
            'received_symbols_real': received_symbols.real.tolist(),
            'received_symbols_imag': received_symbols.imag.tolist(),
            'received_symbols_pre_offset_real': pre_offset_real,
            'received_symbols_pre_offset_imag': pre_offset_imag,
        })

        # Compute some statistics (these can also be probed)
        power_db = 10 * np.log10(np.mean(np.abs(received_symbols) ** 2))
        peak_to_avg = np.max(np.abs(received_symbols)) / np.mean(np.abs(received_symbols))

        # Short delay
        time.sleep(0.01)

    # Write expected values to JSON for test verification
    with open('/tmp/dsp_demo_two_frames_expected.json', 'w') as f:
        json.dump(expected_data, f)


if __name__ == "__main__":
    main()
