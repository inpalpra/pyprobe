# PyProbe Multi-Scale Overlay Spec

This spec defines approaches for comparing overlaid signals with different magnitudes.  
**Status**: Deferred (not part of M2.5)

---

## Motivation

In DSP workflows, overlaid signals may differ by orders of magnitude:
- Output vs error signal
- Signal vs residual
- Magnitude vs metric

A single shared Y-axis may obscure meaningful structure in smaller signals.

---

## Approaches

Two approaches are defined: **Dual Y-Axis** and **Normalization Modes**.  
Implementation should prioritize Normalized mode (simpler) before Dual Y-Axis.

---

# Option A: Normalization Modes

## Core Concept

Instead of adding a second Y-axis, transform overlaid traces to fit the primary axis scale.

## View Modes (User-Selectable)

| Mode | Behavior | Y-Axis Shows |
|------|----------|--------------|
| **Absolute** (default) | All traces use same scale, first trace defines range | Actual values |
| **Normalized** | All traces affine-mapped to first trace's range | First trace's units |
| **RMS Unity** | All traces divided by their RMS | Fixed ±3 range |
| **Stacked** | Traces offset vertically, independent scaling | Per-trace mini-axes |

## Normalized Mode (Affine Transform)

**Principle**: First trace defines the reference scale; subsequent traces are mapped to that range.

### Algorithm

Let `T1` be the first (reference) trace with bounds `[T1_min, T1_max]`.  
For each subsequent trace `Tn`:

```
Tn_normalized = (T1_max - T1_min) * (Tn - Tn_min) / (Tn_max - Tn_min) + T1_min
```

### Behavior

- First trace displays at **true scale** (no transform)
- Subsequent traces are affine-mapped to first trace's value range
- Shapes align visually; relative structure is preserved
- Y-axis labels show first trace's actual values

### Visual Indicator

When Normalized mode is active:
- Mode indicator badge visible on plot
- Normalized traces show small "~" prefix in legend (e.g., "~error")
- Tooltip on trace shows original value, not transformed value

## RMS Unity Mode

**Principle**: All traces normalized by their RMS, displayed on fixed ±3 range (covers 3σ).

### Algorithm

```
Tn_rms = Tn / rms(Tn)
```

### Behavior

- All traces centered around 0
- Y-axis fixed at ±3 (not ±1, to accommodate outliers)
- Useful for comparing relative waveform shapes
- Absolute magnitude information is lost

### Visual Indicator

- Y-axis labeled "× RMS" or "σ"
- Mode badge visible

---

# Option B: Dual Y-Axis

## Core Principles

- Dual Y-Axis is **explicit**, not automatic
- No hidden thresholds or magnitude detection
- No implicit reassignment without user action
- Must not compromise simplicity of single-axis overlays

---

## Axis Model

Each plot MAY have:
- **Primary Y-Axis (Left)** — always exists
- **Secondary Y-Axis (Right)** — optional, created on demand

Each signal is bound to exactly ONE Y-axis.

---

## Signal-to-Axis Assignment

### Default Behavior
- First signal added → Primary Y-Axis (Left)
- Additional signals → Primary Y-Axis unless user explicitly reassigns

### Explicit Reassignment (Required)
- User action required to move a signal to Secondary Y-Axis
- Possible gestures (choose one in implementation):
  - Drag legend entry to right axis region
  - Context menu on signal: "Move to Right Axis"

No automatic magnitude-based reassignment.

---

## Visual Requirements

- Left and right Y-axes must be visually distinct
- Axis tick/label color MUST match associated signal color(s)
- When hovering a signal:
  - Its owning Y-axis is highlighted
- When interacting with an axis:
  - Only signals bound to that axis are affected

---

## Axis Interaction Semantics

- Pinning, zooming, panning, min/max edits apply PER Y-axis
- Left and right Y-axes have independent:
  - Pin state
  - Min/max bounds
  - Autoscale behavior

Reset behavior:
- `R` resets BOTH Y-axes to AUTO
- Future enhancement may allow per-axis reset

---

## Overlay Rules (Dual-Axis Mode)

- X-axis is always shared
- Y-axis operations affect only the active axis
- Cross-axis sync is NOT automatic

---

# Non-Goals (Explicitly Out of Scope)

- Automatic magnitude detection
- Log/linear mixed modes
- More than two Y-axes
- Per-signal autoscale policies

---

# Implementation Priority

| Priority | Feature | Rationale |
|----------|---------|-----------|
| 1 | Normalized mode | Simplest, no new axis UI |
| 2 | RMS Unity mode | Common DSP use case |
| 3 | Dual Y-Axis | Most complex, rare need |
| 4 | Stacked mode | Nice-to-have |

---

# Acceptance Criteria (When Implemented)

Multi-scale overlay support is correct only if:
- Single-axis absolute mode remains simple and unchanged
- Active mode is always visible and obvious
- Users never wonder "is this the real value?"
- No transform occurs without explicit user action
- Normalized traces clearly indicate they are transformed