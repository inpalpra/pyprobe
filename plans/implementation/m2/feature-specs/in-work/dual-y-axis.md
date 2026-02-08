# PyProbe Dual Y-Axis Overlay

This spec defines optional Dual Y-Axis behavior for overlaid signals.
It is NOT part of the current core interaction model.

---

## Motivation

In DSP workflows, overlaid signals may differ by orders of magnitude:
- Output vs error signal
- Signal vs residual
- Magnitude vs metric

A single shared Y-axis may obscure meaningful structure.

---

## Core Principles

- Dual Y-Axis is **explicit**, not automatic by default
- No hidden thresholds
- No implicit reassignment without visual confirmation
- Must not compromise simplicity of single-axis overlays

---

## Axis Model

Each plot MAY have:
- **Primary Y-Axis (Left)** — always exists
- **Secondary Y-Axis (Right)** — optional

Each signal is bound to exactly ONE Y-axis.

---

## Signal-to-Axis Assignment

### Default Behavior
- First signal added → Primary Y-Axis (Left)
- Additional signals → Primary Y-Axis unless user explicitly reassigns

### Explicit Reassignment (Required)
- User action required to move a signal to Secondary Y-Axis
- Possible gestures (choose one in implementation):
  - Drag legend entry to right axis
  - Context menu on signal: “Move to Right Axis”

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

## Non-Goals (Explicitly Out of Scope)

- Automatic magnitude detection
- Log/linear mixed modes
- More than two Y-axes
- Per-signal autoscale policies

---

## Acceptance Criteria (When Implemented)

Dual Y-Axis support is correct only if:
- Single-axis overlays remain simple and unchanged
- Dual-axis behavior is always visible and explainable
- Users never wonder “which axis am I editing?”
- No axis assignment occurs without explicit user intent