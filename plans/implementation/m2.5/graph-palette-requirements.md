# PyProbe M2.5: Graph Palette Requirements

**Version**: 1.0  
**Last Updated**: 2026-02-08  
**Status**: Draft for Review

---

## Overview

This document defines requirements for enhanced graph interactions in PyProbe, synthesizing:
1. **Original user intent** — streamlined graph control with visual feedback
2. **ChatGPT recommendations** — consolidated into authoritative specifications
3. **PyProbe architecture constraints** — PyQt6/PyQtGraph, Constitution compliance

The goal is to transform plots from passive displays into *controllable surfaces* that feel responsive and predictable.

---

## Constitution Alignment

All features MUST respect PyProbe's UX Constitution:

| Principle | Graph Palette Application |
|-----------|---------------------------|
| §1 Gesture over Config | All controls via hover+click, no modal dialogs |
| §2 Acknowledge Every Action | Visual feedback for pin/zoom/pan state changes |
| §3 Live Means Live | Parked graphs continue updating |
| §6 Obvious Lifecycle | Clear pinned/unpinned/maximized states |
| §10 Visible Costs | Throttle/downsample indicators when active |
| §11 Discovery over Docs | Translucent hover buttons teach controls |
| §12 Tool Disappears | Controls fade, never obstruct data |

---

## Feature Requirements

### R1: Axis Pinning with Visual Indicator

**Original Intent**: Pin X scale, pin Y scale with visual indicator of pinned state.

#### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R1.1 | X and Y axes can be pinned independently | P0 |
| R1.2 | Unpinned axis = autoscaled on every data update | P0 |
| R1.3 | Pinned axis = frozen, no autoscale | P0 |
| R1.4 | Pin state shown via lock icon (🔒X / 🔒Y) near axis | P0 |
| R1.5 | Indicator placed inside plot area, not external toolbar | P1 |
| R1.6 | Any manual axis modification auto-pins that axis | P0 |
| R1.7 | Keyboard: `X` toggles X-pin, `Y` toggles Y-pin | P1 |

#### State Machine

```
AUTO (default) ─────────────> PINNED
               user touches axis
               (zoom/pan/edit min-max)

PINNED ──────────────────────> AUTO
               user unpins
               (X/Y key toggle or R key)
```

---

### R2: Explicit Min/Max Axis Editing

**Original Intent**: Set max x, min x, max y, min y with visual indicator of set state.

#### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R2.1 | Double-click first tick label → edit min (inline) | P0 |
| R2.2 | Double-click last tick label → edit max (inline) | P0 |
| R2.3 | Inline text edit, no dialog/popup | P0 |
| R2.4 | Enter commits value, Escape cancels | P0 |
| R2.5 | Editing min/max auto-pins that axis | P0 |
| R2.6 | Pinned axis with explicit bounds shows lock icon | P0 |

#### Notes
- This follows LabVIEW-style in-place editing
- The "visual indicator of set state" is the same lock icon as pinning (no separate state)

---

### R3: Double-Click Maximize/Restore

**Original Intent**: Double click to maximize, double click again to restore.

#### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R3.1 | Double-click plot background → toggles maximize/restore | P0 |
| R3.2 | Animation required (150-200ms transition) | P1 |
| R3.3 | Other plots remain alive and updating | P0 |
| R3.4 | Probes, overlays, axis states persist | P0 |
| R3.5 | No modifier keys required | P0 |

#### Hit-Test Priority (Critical)

Maximize must NOT trigger if double-click lands on:

| Priority | Target | Action |
|----------|--------|--------|
| 1 (Highest) | Axis tick label | In-place edit mode |
| 2 | Axis line/region | Ignored |
| 3 | Data traces | Ignored (future: trace selection) |
| 4 (Lowest) | Empty plot background | Toggle maximize |

> [!WARNING]
> Accidental maximize is a UX bug. When in doubt, do nothing.

---

### R4: Minimize (Park) Graphs to Bottom Bar

**Original Intent**: Minimize graphs to bottom bar, restore them back to graph area.

#### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R4.1 | Parked graphs continue receiving data updates | P0 |
| R4.2 | Bottom bar shows: graph title + color key(s) | P0 |
| R4.3 | Bottom bar shows tiny live sparkline preview | P1 |
| R4.4 | Click/drag from bottom bar restores to main area | P0 |
| R4.5 | Parked graphs retain all state (pins, overlays) | P0 |
| R4.6 | No confirmation dialogs | P0 |

#### State Machine

```
ACTIVE (visible in grid) ────> PARKED (bottom bar, still updating)
                        park

PARKED ──────────────────────> ACTIVE
                        restore
```

---

### R5: Signal Overlay (Replaces Axis Sync Grouping)

**Original Intent**: Group graphs together given to sync x scales, y scales, or both.

**Decision**: Axis sync grouping is **dropped** in favor of signal overlay.

#### Rationale
- Sync groups add conceptual complexity
- Overlay on same axes achieves visual correlation without separate state
- Matches how oscilloscopes work (multiple channels, shared timebase)

#### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R5.1 | Drag symbol from code view onto existing graph → overlay | P0 |
| R5.2 | All overlaid signals share same axes | P0 |
| R5.3 | Axis operations affect all signals in graph | P0 |
| R5.4 | Each signal retains own color + legend entry | P0 |
| R5.5 | Signals can be removed independently | P0 |
| R5.6 | Removing last signal clears graph | P0 |
| R5.7 | Valid drop targets highlight on drag | P1 |
| R5.8 | Invalid drops show rejection feedback | P1 |

---

### R6: In-Plot Interaction Buttons

**Original Intent**: Translucent tiny buttons for hand, zoom, zoom-x, zoom-y, reset, pointer.

#### Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R6.1 | Buttons: Pan, Zoom, Zoom-X, Zoom-Y, Reset, Pointer | P0 |
| R6.2 | Buttons hidden by default, appear on plot hover | P0 |
| R6.3 | Opacity ≤ 40% when visible | P1 |
| R6.4 | Buttons never obscure data traces | P1 |
| R6.5 | Pointer mode is default | P0 |
| R6.6 | Pan/zoom modes auto-revert to Pointer after action | P0 |
| R6.7 | Escape key always returns to Pointer mode | P0 |
| R6.8 | Cursor icon reflects current mode | P1 |

#### Button Semantics

| Button | Icon | Behavior |
|--------|------|----------|
| Pointer | 🖱️ | Default, click-through to traces |
| Pan | ✋ | Drag to pan (auto-pins affected axes) |
| Zoom | 🔍 | Drag rectangle to zoom both axes |
| Zoom-X | ↔️ | Drag to zoom X only |
| Zoom-Y | ↕️ | Drag to zoom Y only |
| Reset | ⟲ | Unpin + autoscale both axes |

---

### R7: Keyboard Shortcuts

**Original Intent**: Implied by wanting discoverable control surface.

| Key | Action | Scope |
|-----|--------|-------|
| `X` | Toggle X-axis pin | Focused plot |
| `Y` | Toggle Y-axis pin | Focused plot |
| `R` | Reset view (unpin + autoscale) | Focused plot |
| `Escape` | Return to Pointer mode | Any plot |

---

## Deferred Features

### Dual Y-Axis Support

**Status**: Deferred per user request.

When implemented:
- Primary Y-Axis (left) always exists
- Secondary Y-Axis (right) is optional
- Explicit user gesture required to assign signal to right axis
- No automatic magnitude-based assignment
- See `m2/feature-specs/in-work/dual-y-axis.md` for full spec

---

## Architectural Considerations

### Current Stack
- **GUI Framework**: PyQt6
- **Charting**: PyQtGraph
- **Plot Base**: `BasePlot` → `WaveformPlot`, `ConstellationPlot`, etc.
- **Container**: `ProbePanel` → `ProbePanelContainer` (grid layout)

### Impact Areas

| Feature | Files Affected |
|---------|----------------|
| Axis pinning | `plots/base_plot.py`, `plots/waveform_plot.py` |
| Min/max editing | New: `gui/axis_editor.py`, modify PyQtGraph axis items |
| Maximize/restore | `gui/probe_panel.py`, `gui/main_window.py` |
| Park to bottom bar | New: `gui/dock_bar.py`, modify `main_window.py` |
| Signal overlay | `gui/code_viewer.py` (drag source), `gui/probe_panel.py` (drop target) |
| Interaction buttons | New: `gui/plot_toolbar.py` (translucent overlay) |

### PyQtGraph Integration Points

- `PlotItem.setXRange()`, `setYRange()` — for pinning
- `PlotItem.enableAutoRange()` — disable when pinned
- `AxisItem` — custom subclass for inline editing
- `ViewBox.mouseDragEvent()` — for zoom rectangle modes

---

## Invariants

These rules MUST hold at all times:

1. **AUTO and PINNED are mutually exclusive** per axis
2. **Autoscale never runs on pinned axis**
3. **Manual action always pins**
4. **No silent state transitions** — every state change is visible
5. **No modifier-key-only behaviors**
6. **No dialog-based interactions**

---

## Acceptance Criteria

Graph palette is correct if:

- [ ] Users never wonder why a plot changed scale
- [ ] Users never wonder why a plot did NOT change scale
- [ ] Overlaying signals feels obvious and discoverable
- [ ] Axis behavior is predictable after 5 seconds of use
- [ ] The plot feels like a **surface**, not a **widget**
- [ ] Controls appear on hover, never obstruct data

Violations require redesign, not documentation workarounds.

---

## Implementation Priority

| Phase | Features | Rationale |
|-------|----------|-----------|
| 1 | R1 (Pinning), R2 (Min/Max), R6 (Buttons partially) | Core interaction quality |
| 2 | R3 (Maximize), R4 (Park), R7 (Keyboard) | Layout control |
| 3 | R5 (Overlay), R6 (Full hover behavior) | Multi-signal workflows |

---

## Open Questions

1. **Park bar location**: Bottom vs collapsible sidebar?
2. **Overlay limit**: Max signals per graph (5? 10? unlimited)?
3. **Icon style**: Unicode emoji vs custom SVG icons?
4. **Focus model**: How does a plot gain keyboard focus?

---

## References

- [graph-palette.md](file:///Users/ppal/repos/pyprobe/plans/implementation/m2/feature-specs/in-work/graph-palette.md) — ChatGPT consolidated spec
- [dual-y-axis.md](file:///Users/ppal/repos/pyprobe/plans/implementation/m2/feature-specs/in-work/dual-y-axis.md) — Deferred spec
- [CONSTITUTION.md](file:///Users/ppal/repos/pyprobe/CONSTITUTION.md) — UX principles
