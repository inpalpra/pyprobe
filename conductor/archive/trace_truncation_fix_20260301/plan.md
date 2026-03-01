# Implementation Plan: Fix Trace Truncation and Zoom/Decimation UX Bug
## Phase 1: Research & Reproduction [checkpoint: eb325e9]
Goal: Identify every downsampling code path in the codebase, determine which ones violate the `[0, N-1]` boundary invariant, and establish a failing baseline.

- [x] Task: Identify Downsampling Code Paths
    - [x] Search the codebase for all `downsample` function/method definitions (there may be more than one implementation).
    - [x] Trace the class hierarchy of each lens widget (Waveform, FFT Mag & Phase, Constellation, complex-plot lenses) to determine which downsample implementation each one actually calls — do not assume from the lens name.
    - [x] For each downsample implementation found, check whether it covers the full input range `[0, N-1]` or truncates a remainder.
    - [x] Document which code paths are affected and which are already correct.
- [x] Task: Explain the Mag vs Phase Asymmetry
    - [x] In `dsp_demo.py`, the `FFT Mag & Phase` lens renders both Magnitude and Phase on the same graph from identically-sized arrays. Yet only the Magnitude trace visibly truncates — the Phase trace appears complete. Investigate and document why these two traces on the same widget follow different rendering paths or use different downsampling parameters, and how that causes one to truncate while the other does not.
- [x] Task: Create Failing Regression Test
    - [x] Create `tests/gui/test_trace_truncation_repro.py`.
    - [x] For every distinct downsample implementation found above, write a test that calls it with an array of length N and asserts that the first sample of the downsampled output equals the first sample of the original array, and the last sample of the downsampled output equals the last sample of the original array. No boundary samples may be silently dropped.
    - [x] Exercise at least these array lengths: 10007 (prime), 8192 (power-of-two), 8193 (power-of-two-plus-one).
    - [x] Include a test that the Phase trace in `FFT Mag & Phase` reaches the last frequency bin, not just the Magnitude trace.
    - [x] Check whether existing tests (e.g. `test_downsample_bug.py`) already partially cover this — strengthen their assertions if so, rather than duplicating.
    - [x] **CRITICAL:** Confirm that these tests fail with the current codebase.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Research & Reproduction' (Protocol in workflow.md)

## Phase 2: Implementation (TDD) [checkpoint: d8acfa5]
Goal: Fix every downsample code path that violates the `[0, N-1]` invariant, as identified in Phase 1.

- [x] Task: Fix Waveform Plot Downsampling
    - [x] Modify the Waveform widget's downsample path to include the last sample correctly.
    - [x] Ensure the x-indices span `[0, N-1]`.
    - [x] Verify fix with `tests/gui/test_trace_truncation_repro.py`.
    - [x] After each fix, confirm the corresponding regression tests from Phase 1 now pass.
- [x] Task: Verify FFT Mag & Phase End-to-End
    - [x] Confirm the FFT Mag & Phase lens (which inherits its downsample from whichever base class it extends) benefits from the fix.
    - [x] Verify both the Magnitude and Phase traces independently reach the last frequency bin.
- [x] Task: Verify General Downsampling Integrity
    - [x] Confirm all downsample paths in the codebase now satisfy the `[0, N-1]` rule.
    - [x] All regression tests from Phase 1 pass.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Implementation (TDD)' (Protocol in workflow.md)

## Phase 3: Final Verification & Cleanup [checkpoint: a955ee5]
Goal: Ensure no regressions and confirm the fix in the actual application.

- [x] Task: Run Full Test Suite
    - [x] Run all existing GUI and Core tests to ensure no regressions in axis synchronization or rendering.
- [x] Task: Manual Verification with `dsp_demo.py`
    - [x] Run `examples/dsp_demo.py`.
    - [x] Verify `FFT Mag & Phase` lens shows no truncation (both Magnitude and Phase).
    - [x] Verify `Waveform` lens shows no truncation.
    - [x] Verify `Constellation` lens shows no truncation.
    - [x] Verify zooming in and out on the right edge of any plot consistently shows the last sample.
    - [x] Verify "Reset Zoom" (double-click or home button) restores the full data range with no missing segments.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Final Verification & Cleanup' (Protocol in workflow.md)
