import numpy as np
import argparse
import matplotlib.pyplot as plt

# -----------------------------
# Nyquist spectra definitions
# -----------------------------

def raised_cosine(freq, T, alpha):
    """
    Raised Cosine (RC) spectrum P(f)
    freq: normalized frequency (cycles/sample, -0.5..0.5)
    T: symbol period in samples (SPS)
    alpha: roll-off factor
    """
    f = np.abs(freq)
    P = np.zeros_like(f)

    f1 = (1 - alpha) / (2 * T)
    f2 = (1 + alpha) / (2 * T)

    P[f <= f1] = T
    mask = (f > f1) & (f <= f2)
    P[mask] = (T / 2) * (
        1 + np.cos(
            np.pi * T / alpha * (f[mask] - f1)
        )
    )
    return P


def root_raised_cosine(freq, T, alpha):
    """
    Root Raised Cosine (RRC) spectrum
    """
    return np.sqrt(raised_cosine(freq, T, alpha))


# -----------------------------
# Equalizer design (Option C)
# -----------------------------

def design_equalizer(
    h,
    sps=16,
    fft_len=4096,
    pulse="rc",
    alpha=0.25,
    eps=1e-6,
    taps=129,
):
    """
    Option C: Frequency-domain pulse shaping equalizer
    """

    # FFT grid
    freq = np.fft.fftfreq(fft_len, d=1.0)
    freq = np.fft.fftshift(freq)

    # Channel spectrum
    H = np.fft.fftshift(np.fft.fft(h, fft_len))

    # Desired Nyquist spectrum
    T = sps
    if pulse.lower() == "rc":
        P = raised_cosine(freq, T, alpha)
    elif pulse.lower() == "rrc":
        P = root_raised_cosine(freq, T, alpha)
    else:
        raise ValueError("Unsupported pulse type")

    # Regularized inversion: W = P * H* / (|H|^2 + eps)
    W = P * np.conj(H) / (np.abs(H) ** 2 + eps)

    # Time-domain equalizer
    # IFFT output is circular (peak at index 0 and end of array)
    w_circular = np.fft.ifft(np.fft.ifftshift(W)).real

    # FIX: Shift the peak to the center of the buffer before truncating
    w_full = np.fft.fftshift(w_circular)

    # Center and truncate
    mid = len(w_full) // 2
    K = taps // 2
    w = w_full[mid - K : mid + K + 1]

    # Normalize gain at symbol sampling point (approximated by sum for BPSK)
    w /= np.sum(w)

    return w


# -----------------------------
# Main
# -----------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nyquist Pulse-Shaping Equalizer (Option C)")
    parser.add_argument("--sps", type=int, default=16)
    parser.add_argument("--pulse", choices=["rc", "rrc"], default="rc")
    parser.add_argument("--alpha", type=float, default=0.25)
    parser.add_argument("--taps", type=int, default=129)
    parser.add_argument("--fft_len", type=int, default=4096)
    parser.add_argument("--eps", type=float, default=1e-6)

    args = parser.parse_args()

    # Provided channel taps h[n]
    h = np.array([
        1.73303E-16, -1.04334E-11, -2.2666E-10, -1.62805E-9, -5.44258E-9, 
        -9.8838E-9, -1.19897E-8, -2.14605E-8, -1.6708E-9, 4.89111E-7, 
        3.18751E-6, 1.2174E-5, 3.34628E-5, 7.05969E-5, 0.000114279, 
        0.000126525, 2.43561E-5, -0.000324706, -0.00107754, -0.00234657, 
        -0.00408442, -0.00593909, -0.00711663, -0.00630082, -0.00167546, 
        0.00892589, 0.0277513, 0.0567867, 0.0974041, 0.150073, 0.214192, 
        0.288065, 0.369014, 0.453605, 0.537931, 0.617921, 0.689618, 
        0.749442, 0.794388, 0.822197, 0.831467, 0.82173, 0.793477, 
        0.748133, 0.687977, 0.61603, 0.535885, 0.451502, 0.366956, 
        0.286143, 0.212482, 0.14863, 0.0962559, 0.0559343, 0.0271707, 
        0.00857412, -0.00185228, -0.00635848, -0.00710506, -0.00589715, 
        -0.00403786, -0.0023089, -0.00105299, -0.000311857, 2.92205E-5, 
        0.000127153, 0.000113343, 6.95193E-5, 3.2746E-5, 1.18296E-5, 
        3.06738E-6, 4.61633E-7, -4.3355E-9, -2.11001E-8, -1.19087E-8, 
        -9.81041E-9, -5.31916E-9, -1.56973E-9, -2.11091E-10, -1.08905E-11, 
        6.98931E-13
    ])

    # Design equalizer
    w = design_equalizer(
        h,
        sps=args.sps,
        fft_len=args.fft_len,
        pulse=args.pulse,
        alpha=args.alpha,
        eps=args.eps,
        taps=args.taps,
    )

    # 1. Plot Equalizer Taps
    plt.figure(figsize=(12, 4))
    plt.plot(w, 'b.-')
    plt.title(f"Equalizer Taps (Option C, Pulse={args.pulse.upper()}, alpha={args.alpha})")
    plt.grid(True, alpha=0.3)
    plt.ylabel("Amplitude")
    plt.xlabel("Tap Index")
    plt.show()

    # --- VERIFICATION PLOT ---
    # Total System Response = Channel * Equalizer
    h_sys = np.convolve(h, w)
    peak_idx = np.argmax(np.abs(h_sys))
    
    # Time axis centered at peak
    t_axis = np.arange(len(h_sys)) - peak_idx
    
    plt.figure(figsize=(12, 6))
    plt.plot(t_axis, h_sys, 'b-', label='Total Impulse Response')
    
    # Identify Symbol Points (Green) and T/2 Points (Red)
    markers_sym = np.arange(-5, 6) * args.sps
    markers_mid = markers_sym + (args.sps // 2)

    # Robust plotting logic to avoid IndexError
    def get_valid_points(offsets):
        valid_offsets = []
        valid_values = []
        for offset in offsets:
            idx = peak_idx + offset
            if 0 <= idx < len(h_sys):
                valid_offsets.append(offset)
                valid_values.append(h_sys[idx])
        return np.array(valid_offsets), np.array(valid_values)

    sym_x, sym_y = get_valid_points(markers_sym)
    mid_x, mid_y = get_valid_points(markers_mid)

    plt.plot(sym_x, sym_y, 'go', markersize=8, label='Symbol Sampling Points (Target: 1, 0, ...)')
    plt.plot(mid_x, mid_y, 'rx', markersize=8, label='T/2 Points (Target: 0)')

    plt.title("Combined System Response (Channel * Equalizer)")
    plt.xlabel("Samples (relative to peak)")
    plt.ylabel("Amplitude")
    plt.xlim(-100, 100)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend()
    plt.show()

    print(f"Equalizer designed successfully with {len(w)} taps.")