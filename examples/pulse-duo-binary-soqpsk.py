import numpy as np
import matplotlib.pyplot as plt

def build_conv_matrix(x, tap_indices, sample_indices):
    """Builds the observation matrix for the given sample locations."""
    M, L = len(sample_indices), len(tap_indices)
    X = np.zeros((M, L))
    for i, n in enumerate(sample_indices):
        for j, k in enumerate(tap_indices):
            idx = int(n - k)
            if 0 <= idx < len(x):
                X[i, j] = x[idx]
    return X

def design_equalizer_matrix_surgical(x, b, SPS, K, alpha_weight=0.5):
    """
    Option B+: Time-domain matrix inversion with T/2 constraints.
    alpha_weight: How aggressively to force the T/2 nulls (0.1 to 1.0).
    """
    # 1. Automatic Timing Alignment
    b_upsample = np.zeros(len(b) * SPS)
    b_upsample[::SPS] = b
    timing = np.argmax(np.correlate(x, b_upsample, mode='full')) - (len(b_upsample) - 1)
    
    tap_idx = np.arange(-K, K + 1)
    
    # 2. Define our targets
    sym_idx = np.arange(len(b)) * SPS + timing      # The T points
    mid_idx = sym_idx + SPS // 2                    # The T/2 points

    # 3. Build Matrices
    Xs = build_conv_matrix(x, tap_idx, sym_idx)      # Matrix for symbol centers
    Xm = build_conv_matrix(x, tap_idx, mid_idx)      # Matrix for mid-points

    # 4. Solve the Regularized Normal Equations
    # Objective: Minimize ||Xs@h - b||^2 + alpha_weight * ||Xm@h||^2
    A = Xs.T @ Xs + alpha_weight * (Xm.T @ Xm)
    
    # Add Ridge Regularization (White Noise Floor) to prevent the " joke" ringing
    # This forces the taps to die out at the edges.
    A += 1e-4 * np.trace(A) / len(tap_idx) * np.eye(len(tap_idx))
    
    rhs = Xs.T @ b
    h = np.linalg.solve(A, rhs)
    
    return h, timing

# --- Execution ---
SPS = 16
K = 60 # 121 total taps
alpha_weight = 0.5 # Surgical knob for T/2 null depth

# h_eq is your equalizer, timing is the offset
h_eq, timing = design_equalizer_matrix_surgical(x, b, SPS, K, alpha_weight)

# --- Verification ---
# Convolve with your original channel w0
h_sys = np.convolve(w0, h_eq) 
pk = np.argmax(np.abs(h_sys))
t = np.arange(len(h_sys)) - pk

plt.figure(figsize=(10, 5))
plt.plot(t, h_sys / np.max(h_sys), 'b-', label='System Response')
plt.plot(np.arange(-3, 4)*SPS, h_sys[pk + np.arange(-3, 4)*SPS]/np.max(h_sys), 'go', label='Symbols (T)')
plt.plot(np.arange(-3, 4)*SPS + SPS//2, h_sys[pk + np.arange(-3, 4)*SPS + SPS//2]/np.max(h_sys), 'rx', label='Mid-points (T/2)')
plt.xlim(-80, 80); plt.grid(True); plt.legend(); plt.title("Option B+: Exact T/2 Nulling")
plt.show()