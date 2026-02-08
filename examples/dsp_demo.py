"""
Example DSP script demonstrating PyProbe capabilities.

Run with: python -m pyprobe examples/dsp_demo.py

Then add these variables to the watch list:
  - received_symbols (constellation diagram)
  - signal_i (waveform)
  - signal_q (waveform)
  - snr_db (scalar)
"""

import numpy as np
import time

# Simulation parameters
NUM_SYMBOLS = 500
NUM_FRAMES = 50

# QAM-16 constellation points
QAM16_CONSTELLATION = np.array([
    -3-3j, -3-1j, -3+1j, -3+3j,
    -1-3j, -1-1j, -1+1j, -1+3j,
    +1-3j, +1-1j, +1+1j, +1+3j,
    +3-3j, +3-1j, +3+1j, +3+3j
]) / np.sqrt(10)  # Normalize power


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
    signal_i = received_symbols.real
    signal_q = received_symbols.imag

    return received_symbols, signal_i, signal_q


def main():
    """Main processing loop."""
    # print("=" * 50)
    # print("PyProbe DSP Demo")
    # print("=" * 50)
    # print()
    # print("Add these variables to the watch list:")
    # print("  - received_symbols (constellation diagram)")
    # print("  - signal_i (waveform)")
    # print("  - signal_q (waveform)")
    # print("  - snr_db (scalar)")
    # print()
    # print("Starting signal generation...")
    # print()

    for frame in range(NUM_FRAMES):
        # Vary SNR over time (15-25 dB)
        snr_db = 20 + 5 * np.sin(2 * np.pi * frame / 50)

        # Generate QAM signal with noise
        received_symbols, signal_i, signal_q = generate_qam_signal(
            NUM_SYMBOLS, snr_db
        )

        # Compute some statistics (these can also be probed)
        power_db = 10 * np.log10(np.mean(np.abs(received_symbols) ** 2))
        peak_to_avg = np.max(np.abs(received_symbols)) / np.mean(np.abs(received_symbols))

        # Print progress
        # print(f"Frame {frame + 1:3d}/{NUM_FRAMES}: "
        #       f"SNR={snr_db:.1f} dB, "
        #       f"Power={power_db:.2f} dB, "
        #       f"PAPR={20*np.log10(peak_to_avg):.1f} dB")

        # Simulate processing time
        time.sleep(0.05)  # 50ms per frame = ~20 FPS

    print()
    print("Demo complete!")


if __name__ == "__main__":
    main()
