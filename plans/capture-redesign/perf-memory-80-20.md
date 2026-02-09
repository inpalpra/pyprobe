# 80/20 Performance and Memory Optimizations

This document outlines the highest-leverage (80/20) optimizations to pursue after Milestone 8. The goal is to keep capture lossless while preventing UI stalls and unbounded memory growth in long-running sessions.

## Principles

- Preserve correctness: do not drop captures by default.
- Optimize the display path, not the capture path.
- Prefer incremental, low-risk changes that yield big wins.

## Performance: Top 20% Changes That Deliver 80% of Benefit

### 1) Batch redraw work and coalesce updates

- Redraw at a fixed maximum rate (e.g., 60 FPS) using the existing `RedrawThrottler`.
- If multiple batches arrive between redraws, render once using the full buffer.
- Avoid per-capture UI updates; always render from buffers.

Expected impact: major reduction in UI thread load in tight loops.

### 2) Avoid redundant plot re-creation

- Keep plot widgets stable; avoid re-instantiating plots on dtype changes unless required.
- Cache per-panel plot instances and reuse them when possible.

Expected impact: fewer expensive widget operations and smoother UI.

### 3) Downsample for display only

- Keep full capture history in buffers.
- When rendering large arrays or long histories, downsample the data for display only.
- Make downsampling deterministic so repeated renders are consistent.

Expected impact: large plots remain responsive without data loss.

### 4) Limit per-frame processing work

- Cap the number of IPC messages processed per polling tick (already present).
- If backlog grows, prioritize processing batches to reduce overhead.

Expected impact: keeps GUI responsive even with message spikes.

### 5) Minimize serialization overhead in hot paths

- Avoid repeated conversions for the same data in a single render pass.
- Keep capture serialization minimal; do any expensive formatting only in display logic.

Expected impact: reduces CPU pressure in tracer and GUI.

## Memory: Top 20% Changes That Deliver 80% of Benefit

### 1) Optional ring buffer mode per probe

- Add a configurable max history length per probe.
- Default to unlimited for correctness; allow users to cap history for long runs.
- When enabled, keep the most recent N samples and expose the truncation in UI.

Expected impact: prevents unbounded memory growth in long-running sessions.

### 2) Chunked storage for large histories

- Store history in fixed-size chunks to reduce reallocations and memory fragmentation.
- This is especially effective for scalar history and time-series data.

Expected impact: lower memory churn and fewer large reallocations.

### 3) Store timestamps as relative offsets

- Store timestamps as offsets from the first sample (int ns).
- This can reduce memory for large timestamp arrays and simplify axis scaling.

Expected impact: small but consistent memory savings across large buffers.

### 4) Release buffers on probe removal

- Ensure all buffers, plots, and overlays are dropped when a probe is removed.
- Confirm any overlay-only probes are fully cleaned up.

Expected impact: prevents gradual memory creep over session length.

## Suggested Implementation Order

1) Enforce redraw coalescing in GUI (already mostly done via `RedrawThrottler`).
2) Add optional ring buffer mode for `ProbeDataBuffer`.
3) Implement display-only downsampling for large histories.
4) Add chunked storage if needed after profiling.

## What Not To Do (Yet)

- Do not drop captures automatically; only allow explicit user opt-in.
- Do not introduce global sampling that changes data correctness.
- Avoid complex concurrency changes until profiling proves it is needed.

## How To Validate Improvements

- Use the 1M-iteration test to verify no data loss.
- Measure GUI frame rate while capturing high-frequency updates.
- Track memory usage over long runs with and without ring buffer mode.

## Open Questions

- Default history cap (if any) for new probes.
- Should downsampling be probe-type specific (scalar vs waveform)?
- How to surface “history truncated” state in the UI.
