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

    # Regularized inversion
    W = P * np.conj(H) / (np.abs(H) ** 2 + eps)

    # # Time-domain equalizer
    # w = np.fft.ifft(np.fft.ifftshift(W)).real

    # # Center and truncate
    # mid = len(w) // 2
    # K = taps // 2
    # w = w[mid - K : mid + K + 1]

    # FIX: Shift the zero-frequency component to the center of the spectrum
    w = np.fft.fftshift(w)

    # Center and truncate
    mid = len(w) // 2
    K = taps // 2
    # Now 'mid' actually contains the peak
    w = w[mid - K : mid + K + 1]

    # Normalize gain at symbol sampling
    w /= np.sum(w)

    return w


# -----------------------------
# Main
# -----------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nyquist Pulse-Shaping Equalizer (Option C)")
    parser.add_argument("--sps", type=int, default=16)
    parser.add_argument("--pulse", choices=["rc", "rrc"], default="rc")
    parser.add_argument("--alpha", type=float, default=0.50)
    parser.add_argument("--taps", type=int, default=129)
    parser.add_argument("--fft_len", type=int, default=4096)
    parser.add_argument("--eps", type=float, default=1e-6)

    args = parser.parse_args()

    # Load channel taps
    h = np.array([1.73303E-16, -1.04334E-11, -2.2666E-10, -1.62805E-9, -5.44258E-9, -9.8838E-9, -1.19897E-8, -2.14605E-8, -1.6708E-9, 4.89111E-7, 3.18751E-6, 1.2174E-5, 3.34628E-5, 7.05969E-5, 0.000114279, 0.000126525, 2.43561E-5, -0.000324706, -0.00107754, -0.00234657, -0.00408442, -0.00593909, -0.00711663, -0.00630082, -0.00167546, 0.00892589, 0.0277513, 0.0567867, 0.0974041, 0.150073, 0.214192, 0.288065, 0.369014, 0.453605, 0.537931, 0.617921, 0.689618, 0.749442, 0.794388, 0.822197, 0.831467, 0.82173, 0.793477, 0.748133, 0.687977, 0.61603, 0.535885, 0.451502, 0.366956, 0.286143, 0.212482, 0.14863, 0.0962559, 0.0559343, 0.0271707, 0.00857412, -0.00185228, -0.00635848, -0.00710506, -0.00589715, -0.00403786, -0.0023089, -0.00105299, -0.000311857, 2.92205E-5, 0.000127153, 0.000113343, 6.95193E-5, 3.2746E-5, 1.18296E-5, 3.06738E-6, 4.61633E-7, -4.3355E-9, -2.11001E-8, -1.19087E-8, -9.81041E-9, -5.31916E-9, -1.56973E-9, -2.11091E-10, -1.08905E-11, 6.98931E-13])

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

    # Save equalizer taps
    # np.savetxt("examples/soqpsk/equalizer_taps.txt", w)

    plt.figure(figsize=(16, 4))
    plt.plot(w)
    plt.title("Equalizer taps")
    plt.grid(True)
    plt.show()

    # --- VERIFICATION PLOT ---
    # Convolve Channel (w0) with Equalizer (w) to see the total system response
    h_sys = np.convolve(h, w)
    
    # Find the peak of the system response to align the plot
    peak_idx = np.argmax(np.abs(h_sys))
    
    # Generate indices for plotting
    t_axis = np.arange(len(h_sys)) - peak_idx
    
    plt.figure(figsize=(12, 6))
    
    # 1. Plot the Total Response
    plt.plot(t_axis, h_sys, 'b-', label='Total Impulse Response')
    
    # 2. Mark the Symbol Sampling Points (should be 1.0 at 0, 0 elsewhere)
    # We look at a window of +/- 3 symbols
    markers_sym = np.arange(-3, 4) * args.sps
    plt.plot(markers_sym, h_sys[peak_idx + markers_sym], 'go', label='Symbol Points (Target=1/0)')
    
    # 3. Mark the T/2 Points (should be ~0 based on your design)
    markers_mid = markers_sym + (args.sps // 2)
    # Filter out indices that might be out of bounds
    valid_mid = [m for m in markers_mid if 0 <= peak_idx + m < len(h_sys)]
    plt.plot(valid_mid, h_sys[peak_idx + np.array(valid_mid)], 'rx', label='T/2 Points (Target=0)')
    
    plt.title("Total System Response (Channel * Equalizer)")
    plt.xlim(-50, 50) # Zoom in near the main lobe
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.show()