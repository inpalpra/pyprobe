# Specification: Fix Trace Truncation and Zoom/Decimation UX Bug

## Overview
A UX bug exists where traces (particularly in the `FFT Mag & Phase` lens, but potentially elsewhere) are visually truncated on the right side (highest indices) in the default "full" view. Approximately the last 10% of the trace is missing. Zooming into the affected area correctly reveals the missing data, but resetting the zoom or the initial render consistently hides it. This renders the default view of the graphs unreliable for signal analysis.

## Problem Description
- **Symptoms:** The right-most segment of a trace is not rendered in the default/reset view.
- **Observed In:** `FFT Mag & Phase` lens (Magnitude trace specifically reported). The Phase trace and the plain `Waveform` lens may also be affected for sufficiently large arrays.
- **Reproduction:** Run `examples/dsp_demo.py`, switch to `FFT Mag & Phase` lens, and observe the Magnitude plot.
- **Persistence:** The issue persists across data updates. Zooming in reveals the data; resetting zoom hides it again.
- **Likely Root Cause:** Incorrect bounding box calculation or downsampling indexing logic when the `ViewBox` is set to the full range of the data. The "Intelligent Zoom-Responsive Downsampling" system may be excluding the final points of the buffer when calculating the downsampled set for the full-view threshold.

## Functional Requirements
- **Complete Trace Rendering:** All points in the data buffer must be visually represented in the plot, regardless of zoom level. This applies to every downsample code path in the codebase, not just the one triggering the reported symptom.
- **Accurate Default View:** The "Reset Zoom" (full view) action must correctly calculate the data bounds and ensure the entire trace is visible.
- **Consistent Behavior Across Lenses:** The fix must be verified for all lenses (Waveform, FFT Mag & Phase, Constellation) and data types (Real, Complex). Both the Magnitude and Phase traces in dual-axis views must be verified independently.
- **Downsampling Integrity:** The downsampling logic must include the first and last points of the visible range to avoid visual "drift" or truncation at the boundaries. For any input array of length N, the downsampled output x-indices must span the closed interval `[0, N-1]`.

## Non-Functional Requirements
- **Performance:** Rendering should remain smooth for large datasets (>100k points).
- **Stability:** No regressions in the `ViewBox` auto-ranging or axis synchronization logic.

## Acceptance Criteria
- [ ] Running `examples/dsp_demo.py` and viewing `FFT Mag & Phase` shows the complete magnitude spectrum without truncation.
- [ ] Running `examples/dsp_demo.py` and viewing the plain `Waveform` lens shows the complete trace without truncation.
- [ ] Zooming in and out on the right edge of any plot consistently shows the last sample of the data.
- [ ] The "Reset Zoom" action (double-click or home button) restores the view to the full data range with no missing segments.
- [ ] No regressions in existing GUI tests or plot synchronization.
- [ ] A new regression test must verify: for every downsample code path, given an input array of length N where N is not evenly divisible by the chunk count, the maximum x-index in the downsampled output equals `N - 1`.
- [ ] The regression test must exercise at least these array lengths: a prime number (e.g. 10007), a power-of-two (e.g. 8192), and a power-of-two-plus-one (e.g. 8193).
- [ ] The regression test must cover both the Waveform widget's downsample path and the complex-plot widget's downsample path independently.
- [ ] The Phase trace in `FFT Mag & Phase` must also reach the last frequency bin — not just the Magnitude trace.

## Out of Scope
- Architectural changes to the `pyqtgraph` core (only PyProbe wrappers/plugins should be modified).
- Enhancements to the Equation Editor or other unrelated UI components.
