import numpy as np
import matplotlib.pyplot as plt


def build_conv_matrix(x, tap_indices, sample_indices):
    """
    Build convolution matrix:
    row i = [x[n - k] for k in tap_indices]
    """
    M = len(sample_indices)
    L = len(tap_indices)
    X = np.zeros((M, L))

    for i, n in enumerate(sample_indices):
        for j, k in enumerate(tap_indices):
            idx = n - k
            if 0 <= idx < len(x):
                X[i, j] = x[idx]

    return X


def estimate_symbol_timing(x, b_upsample):
    """
    Estimate symbol timing using correlation
    """
    corr = np.correlate(x, b_upsample, mode='full')
    timing = np.argmax(corr) - (len(b_upsample) - 1)
    return timing


def design_equalizer_option_B(x, b, SPS, K, alpha):
    """
    Option B:
    - Hard symbol recovery
    - Soft mid-symbol suppression
    - Proper timing
    - Regularized solution
    """

    tap_idx = np.arange(-K, K + 1)

    # build upsampled symbols for timing estimation
    b_upsample = np.zeros(len(b) * SPS)
    b_upsample[::SPS] = b

    # estimate timing from received signal
    timing = estimate_symbol_timing(x, b_upsample)

    # symbol and mid-symbol sample locations
    sym_idx = np.arange(len(b)) * SPS + timing
    mid_idx = sym_idx + SPS // 2

    # build convolution matrices
    Xs = build_conv_matrix(x, tap_idx, sym_idx)
    Xm = build_conv_matrix(x, tap_idx, mid_idx)

    # balance mid-symbol penalty
    alpha2 = alpha * np.trace(Xs.T @ Xs) / np.trace(Xm.T @ Xm)
    print(alpha2)

    # normal equations
    A = Xs.T @ Xs + alpha2 * (Xm.T @ Xm)

    # numerical stabilization (ridge)
    eps = 1e-6 * np.trace(A)
    A += eps * np.eye(A.shape[0])

    rhs = Xs.T @ b

    w = np.linalg.solve(A, rhs)

    return w, timing


def main():
    np.random.seed(0)

    SPS = 16
    K = 5 * SPS
    alpha = 0.2

    # random BPSK symbols
    b = np.random.randint(0, 2, 100) * 2 - 1

    # channel impulse response (your w0)
    w0 = np.loadtxt("examples//soqpsk/w0_16sps.txt")

    # upsample symbols
    b_upsample = np.zeros(len(b) * SPS)
    b_upsample[::SPS] = b

    # channel output
    x = np.convolve(b_upsample, w0)

    # design equalizer
    w, timing = design_equalizer_option_B(x, b, SPS, K, alpha)

    print(f"Estimated timing offset: {timing}")

    # plots
    plt.figure(figsize=(16, 4))
    plt.plot(w)
    plt.title("Equalizer taps (Option B)")
    plt.grid(True)
    plt.show()

    # ... after calculating w ...

    # --- VERIFICATION PLOT ---
    # Convolve Channel (w0) with Equalizer (w) to see the total system response
    h_sys = np.convolve(w0, w)
    
    # Find the peak of the system response to align the plot
    peak_idx = np.argmax(np.abs(h_sys))
    
    # Generate indices for plotting
    t_axis = np.arange(len(h_sys)) - peak_idx
    
    plt.figure(figsize=(12, 6))
    
    # 1. Plot the Total Response
    plt.plot(t_axis, h_sys, 'b-', label='Total Impulse Response')
    
    # 2. Mark the Symbol Sampling Points (should be 1.0 at 0, 0 elsewhere)
    # We look at a window of +/- 3 symbols
    markers_sym = np.arange(-3, 4) * SPS
    plt.plot(markers_sym, h_sys[peak_idx + markers_sym], 'go', label='Symbol Points (Target=1/0)')
    
    # 3. Mark the T/2 Points (should be ~0 based on your design)
    markers_mid = markers_sym + (SPS // 2)
    # Filter out indices that might be out of bounds
    valid_mid = [m for m in markers_mid if 0 <= peak_idx + m < len(h_sys)]
    plt.plot(valid_mid, h_sys[peak_idx + np.array(valid_mid)], 'rx', label='T/2 Points (Target=0)')
    
    plt.title("Total System Response (Channel * Equalizer)")
    plt.xlim(-50, 50) # Zoom in near the main lobe
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.show()


if __name__ == "__main__":
    main()