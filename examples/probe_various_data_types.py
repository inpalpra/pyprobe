"""
PyProbe UX Stress Demo
=====================

This script is intentionally designed to exercise:
- Scalars (real + complex)
- 1D arrays (real + complex)
- Struct-like waveforms (LabVIEW cluster analog)
- Arrays of structs
- Ambiguous lines (x = x + 1)
- Late-executing code paths
- Slowly vs rapidly updating signals
- Nested scopes and functions

If PyProbe M1 UX is solid, probing this file should feel effortless.
If not, the pain will be obvious.
"""

from dataclasses import dataclass
import numpy as np
import time
import math
from typing import List


# -----------------------------
# LabVIEW-like waveform cluster
# -----------------------------
@dataclass
class Waveform:
    t0: float        # start time
    dt: float        # sampling interval
    x: np.ndarray    # samples (real or complex)


# -----------------------------
# Scalar generators
# -----------------------------
def scalar_sources(n: int):
    """Generates slowly changing scalar values."""
    real_scalar = 0.0
    complex_scalar = 0.0 + 0.0j

    for k in range(n):
        real_scalar = math.sin(0.1 * k)
        complex_scalar = np.exp(1j * 0.05 * k)

        yield real_scalar, complex_scalar
        time.sleep(0.02)


# -----------------------------
# Array generators
# -----------------------------
def array_sources(n: int, length: int):
    """Generates 1D real and complex arrays."""
    for k in range(n):
        t = np.arange(length)

        real_array = np.sin(2 * np.pi * 0.01 * t + 0.1 * k)
        complex_array = np.exp(1j * (0.02 * t + 0.05 * k))

        yield real_array, complex_array
        time.sleep(0.02)


# -----------------------------
# Waveform generators
# -----------------------------
def waveform_source(n: int, length: int) -> Waveform:
    """Generates a single waveform struct."""
    t0 = time.time()
    dt = 1e-3

    for k in range(n):
        t = np.arange(length) * dt
        x = np.sin(2 * np.pi * 5 * t + 0.1 * k)

        wf = Waveform(t0=t0, dt=dt, x=x)
        yield wf

        t0 += length * dt
        time.sleep(0.03)


def complex_waveform_source(n: int, length: int) -> Waveform:
    """Generates a complex waveform struct."""
    t0 = time.time()
    dt = 5e-4

    for k in range(n):
        t = np.arange(length) * dt
        x = np.exp(1j * (2 * np.pi * 2 * t + 0.2 * k))

        wf = Waveform(t0=t0, dt=dt, x=x)
        yield wf

        t0 += length * dt
        time.sleep(0.03)


# ----------------------------------
# Array of waveform structs (cluster[])
# ----------------------------------
def waveform_bank(num_wf: int, length: int) -> List[Waveform]:
    """Creates an array of waveform structs."""
    base_time = time.time()
    dt = 1e-3

    bank = []
    for i in range(num_wf):
        t = np.arange(length) * dt
        x = np.sin(2 * np.pi * (i + 1) * t)
        bank.append(Waveform(t0=base_time, dt=dt, x=x))

    return bank


# -----------------------------
# Ambiguous / UX-hostile code
# -----------------------------
def ambiguous_math(x):
    # Intentional ambiguity for probing:
    # x appears multiple times on the same line
    x = x + x * 0.1
    return x


# -----------------------------
# Main loop
# -----------------------------
def main():
    num_iters = 500

    # Scalars
    scalar_gen = scalar_sources(num_iters)

    # Arrays
    array_gen = array_sources(num_iters, length=256)

    # Waveforms
    wf_real_gen = waveform_source(num_iters, length=512)
    wf_cplx_gen = complex_waveform_source(num_iters, length=512)

    # Static waveform bank (array of structs)
    wf_bank = waveform_bank(num_wf=3, length=256)

    # Counters & metrics
    iteration = 0
    snr_db = 30.0
    phase_err = 0.0 + 0.0j

    for iteration in range(num_iters):
        # --- Scalars ---
        real_scalar, complex_scalar = next(scalar_gen)

        snr_db = 20 + 10 * math.log10(abs(real_scalar) + 1e-3)
        phase_err = complex_scalar * np.exp(-1j * 0.1)

        # --- Arrays ---
        real_array, complex_array = next(array_gen)

        power_est = np.mean(real_array ** 2)

        # --- Waveforms ---
        wf_real = next(wf_real_gen)
        wf_cplx = next(wf_cplx_gen)

        # --- Ambiguous math ---
        power_est = ambiguous_math(power_est)

        # --- Touch waveform bank (array of clusters) ---
        for i, wf in enumerate(wf_bank):
            wf_bank[i] = Waveform(
                t0=wf.t0,
                dt=wf.dt,
                x=wf.x * math.cos(0.01 * iteration)
            )

        # --- Artificial pacing ---
        time.sleep(0.01)


if __name__ == "__main__":
    main()