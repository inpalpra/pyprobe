# M2.5 Graph Palette — Architectural Overview

## Executive Summary

Graph Palette transforms PyProbe plots from passive displays into **controllable surfaces**. Users can pin axes, edit min/max in-place, maximize/park graphs, overlay signals, and interact via translucent hover buttons.

## System Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              MainWindow                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         ProbePanelContainer                           │  │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐               │  │
│  │  │  ProbePanel   │ │  ProbePanel   │ │  ProbePanel   │  ...          │  │
│  │  │  ┌─────────┐  │ │  ┌─────────┐  │ │  ┌─────────┐  │               │  │
│  │  │  │PlotItem │  │ │  │PlotItem │  │ │  │PlotItem │  │               │  │
│  │  │  │ ┌─────┐ │  │ │  │         │  │ │  │         │  │               │  │
│  │  │  │ │Btn  │ │  │ │  │         │  │ │  │         │  │  MAXIMIZED    │  │
│  │  │  │ │🔒X  │ │  │ │  │         │  │ │  │         │  │  (single view)│  │
│  │  │  │ │🔒Y  │ │  │ │  │         │  │ │  │         │  │               │  │
│  │  │  │ └─────┘ │  │ │  │         │  │ │  │         │  │               │  │
│  │  │  └─────────┘  │ │  └─────────┘  │ │  └─────────┘  │               │  │
│  │  └───────────────┘ └───────────────┘ └───────────────┘               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                           DockBar (parked graphs)                     │  │
│  │  [📈 signal_a] [📈 waveform_1] [📈 fft_out]                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

## New Abstractions

### 1. AxisPinState (per axis)
```
enum AxisPinState:
    AUTO       # Autoscale on every update (default)
    PINNED     # Frozen range, no autoscale
```

**Invariants:**
- AUTO ↔ PINNED are mutually exclusive
- Manual axis modification (zoom/pan/edit) → PINNED
- Reset action → AUTO

### 2. PlotLayoutState (per graph)
```
enum PlotLayoutState:
    ACTIVE     # Visible in grid, normal size
    MAXIMIZED  # Fills container, others hidden
    PARKED     # In DockBar, not visible in grid
```

### 3. InteractionMode (per graph)
```
enum InteractionMode:
    POINTER    # Default, click-through to traces
    PAN        # Drag to pan (auto-pins axes)
    ZOOM       # Drag rectangle, zoom both axes
    ZOOM_X     # Drag horizontal, zoom X only
    ZOOM_Y     # Drag vertical, zoom Y only
```

**Invariant:** Modes revert to POINTER after action completes.

---

## Component Breakdown

| Component | File | Responsibility |
|-----------|------|----------------|
| AxisController | `plots/axis_controller.py` | Manages pin state, autoscale toggle |
| AxisEditor | `gui/axis_editor.py` | Inline min/max editing widget |
| PinIndicator | `plots/pin_indicator.py` | Lock icon overlay on axes |
| PlotToolbar | `gui/plot_toolbar.py` | Translucent hover buttons |
| DockBar | `gui/dock_bar.py` | Parked graphs container |
| LayoutManager | `gui/layout_manager.py` | Maximize/restore orchestration |

---

## Data Flow

### Axis Pinning Flow
```
User touches axis (zoom/pan/edit)
    ↓
WaveformPlot._on_axis_modified()
    ↓
AxisController.set_pinned(axis, True)
    ↓
plot_item.enableAutoRange(axis, False)
PinIndicator.show(axis)
```

### Maximize Flow
```
User double-clicks plot background
    ↓
ViewBox.mouseDoubleClickEvent() — hit-test priority check
    ↓
LayoutManager.toggle_maximize(panel)
    ↓
ProbePanelContainer: hide other panels, expand target
Animation: 150-200ms transition
```

### Signal Overlay Flow
```
User drags symbol from CodeViewer
    ↓
CodeViewer: initiate drag with anchor data
    ↓
ProbePanel.dropEvent(): valid target check
    ↓
ProbePanel.add_overlay(anchor)
    ↓
WaveformPlot: add curve with new color
Legend: add entry
```

---

## Integration Points with Existing Code

| Existing Component | Integration |
|--------------------|-------------|
| `WaveformPlot` | Add AxisController, override ViewBox events |
| `ProbePanel` | Add toolbar overlay, handle maximize/park |
| `ProbePanelContainer` | Add LayoutManager for maximize state |
| `MainWindow` | Add DockBar widget to layout |
| `CodeViewer` | Enable drag initiation (already has probe_requested signal) |

---

## Implementation Phases

### Phase 1: Core Interaction Quality
- R1: Axis pinning + pin indicator
- R2: In-place min/max editing
- R6 (partial): PlotToolbar skeleton with Reset button

### Phase 2: Layout Control
- R3: Double-click maximize/restore
- R4: Park to DockBar
- R7: Keyboard shortcuts + focus model

### Phase 3: Multi-Signal Workflows
- R5: Signal overlay via drag-drop
- R6 (full): All toolbar buttons with hover behavior

---

## Constitution Compliance Checklist

| § | Principle | Implementation |
|---|-----------|----------------|
| 1 | Gesture over Config | Hover+click for all controls |
| 2 | Acknowledge Action | Visual feedback on state change |
| 3 | Live Means Live | Parked graphs continue updating |
| 6 | Obvious Lifecycle | ACTIVE/PINNED/MAXIMIZED/PARKED visible |
| 10 | Visible Costs | Throttle indicator (already exists) |
| 11 | Discovery > Docs | Hover buttons appear on mouse-over |
| 12 | Tool Disappears | Buttons fade, ≤40% opacity |
