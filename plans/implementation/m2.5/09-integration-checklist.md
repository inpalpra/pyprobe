# M2.5 Integration Checklist

Use this checklist to verify complete integration of all Graph Palette components.

---

## Phase 1: Core Interaction Quality

### Axis Pinning (01)
- [ ] `AxisController` instantiated in `WaveformPlot.__init__()`
- [ ] ViewBox `sigRangeChangedManually` connected to `AxisController.set_pinned()`
- [ ] `WaveformPlot.update_data()` checks pin state before autoscale
- [ ] Lock icon appears when axis is pinned
- [ ] Lock icon positioned inside plot area

### In-Place Editing (02)
- [ ] Custom AxisItem subclass intercepts double-click
- [ ] `AxisEditor` appears over clicked tick label
- [ ] Enter commits value, updates range, pins axis
- [ ] Escape cancels without change
- [ ] Invalid (non-numeric) input is rejected

### Plot Toolbar (03)
- [ ] `PlotToolbar` added as child of `ProbePanel`
- [ ] Toolbar hidden by default
- [ ] `ProbePanel.enterEvent()` → `toolbar.show_on_hover()`
- [ ] `ProbePanel.leaveEvent()` → `toolbar.hide_on_leave()`
- [ ] Toolbar opacity ≤ 40%
- [ ] All 6 buttons functional

---

## Phase 2: Layout Control

### Maximize/Restore (04)
- [ ] `LayoutManager` instantiated in `ProbePanelContainer.__init__()`
- [ ] Double-click hit-test correctly excludes axes/traces
- [ ] `maximize_requested` signal from `ProbePanel`
- [ ] Animation 150-200ms
- [ ] Hidden panels continue receiving data
- [ ] Axis states persist across maximize/restore

### DockBar (05)
- [ ] `DockBar` added to `MainWindow` layout (bottom)
- [ ] `park_requested` signal from `ProbePanel` context menu
- [ ] `ProbePanelContainer` handles park transition
- [ ] Parked panels route data to DockBar
- [ ] Click on bar item restores to grid
- [ ] Bar auto-hides when empty

### Keyboard/Focus (07)
- [ ] `FocusManager` instantiated in `ProbePanelContainer.__init__()`
- [ ] `ProbePanel.focusPolicy` set to ClickFocus
- [ ] Focus indicator (cyan glow) on focused panel
- [ ] X/Y/R/Escape keys handled in `ProbePanel.keyPressEvent()`
- [ ] Tab cycles through panels

---

## Phase 3: Multi-Signal Workflows

### Signal Overlay (06)
- [ ] Drag initiation from `CodeViewer`
- [ ] MIME type `application/x-pyprobe-anchor`
- [ ] `ProbePanel.setAcceptDrops(True)`
- [ ] Drop target highlights on dragEnter
- [ ] `overlay_requested` signal emitted
- [ ] `WaveformPlot.add_overlay()` adds curve with new color
- [ ] Legend updated
- [ ] Context menu option to remove overlay
- [ ] Removing last signal clears graph

---

## Data Flow Verification

- [ ] Active panels: `MainWindow._on_variable_data()` → `ProbePanel.update_data()`
- [ ] Maximized panels: Same flow, panel receives data while expanded
- [ ] Parked panels: `MainWindow._on_variable_data()` → `DockBar.update_data()`
- [ ] Overlaid signals: Each overlay anchor routes data to same `WaveformPlot`

---

## Constitution Compliance

- [ ] §1: All controls via hover+click (no dialogs)
- [ ] §2: Visual feedback for every state change
- [ ] §3: Parked graphs continue updating
- [ ] §6: ACTIVE/PINNED/MAXIMIZED/PARKED states visible
- [ ] §10: Throttle indicator visible when active
- [ ] §11: Hover buttons discoverable
- [ ] §12: Controls fade (≤40% opacity)

---

## Final Validation

- [ ] Run full demo script with probes
- [ ] Pin/unpin axes via zoom and keyboard
- [ ] Maximize/restore multiple panels
- [ ] Park panel, verify updates, restore
- [ ] Overlay two signals, verify shared axes
- [ ] Navigate with keyboard (Tab, X, Y, R, Escape)
