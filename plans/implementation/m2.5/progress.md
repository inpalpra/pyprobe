# M2.5 Graph Palette — Implementation Progress

**Session:** 2026-02-08  
**Commit:** `e6ef478` on branch `opus46` — "opus46 m2.5"  
**Diff:** 26 files changed, +1935 / -11 lines

---

## Status: Scaffold Complete, Not Runtime-Verified

All 7 sub-features have code in place. Zero static errors (checked via `get_errors` on all 20 files). **No runtime testing was performed** — the app was not launched, no manual or automated tests were run.

---

## What Was Done

### New Files Created (14 total)

| File | Purpose | Lines |
|------|---------|-------|
| `pyprobe/plots/axis_controller.py` | `AxisController` + `AxisPinState` enum. Listens to `sigRangeChangedManually`, auto-pins on zoom/pan. | 86 |
| `pyprobe/plots/pin_indicator.py` | `PinIndicator` overlay widget. Shows 🔒X / 🔒Y labels, transparent for mouse. | 66 |
| `pyprobe/plots/editable_axis.py` | `EditableAxisItem(pg.AxisItem)`. Emits `edit_min_requested`/`edit_max_requested` on double-click in lower/upper 30% of axis. | 69 |
| `pyprobe/gui/axis_editor.py` | `AxisEditor(QLineEdit)`. Inline number editor. Enter commits, Escape cancels. `QDoubleValidator`. | 110 |
| `pyprobe/gui/plot_toolbar.py` | `PlotToolbar` with `InteractionMode` enum (POINTER/PAN/ZOOM/ZOOM_X/ZOOM_Y). Uses `QGraphicsOpacityEffect`, max 40%. | 164 |
| `pyprobe/gui/icons/` | 6 SVG files (24×24 cyan line art): pointer, pan, zoom, zoom_x, zoom_y, reset. | ~34 |
| `pyprobe/gui/layout_manager.py` | `LayoutManager`. Hides siblings on maximize, restores on toggle. `layout_changed` signal. | 91 |
| `pyprobe/gui/dock_bar.py` | `DockBar` + `DockBarItem` + `ColorDot`. Bottom bar for parked panels, auto-hides when empty. | 151 |
| `pyprobe/gui/drag_helpers.py` | `encode_anchor_mime`, `decode_anchor_mime`, `has_anchor_mime`. MIME type `application/x-pyprobe-anchor`. | 66 |
| `pyprobe/gui/focus_manager.py` | `FocusManager`. Tracks one focused panel, `focus_next()` cycles in list order. | 88 |
| `tests/test_axis_controller.py` | 11 unit tests | 100 |
| `tests/test_axis_editor.py` | 7 unit tests | 66 |
| `tests/test_plot_toolbar.py` | 5 unit tests | 52 |
| `tests/test_layout_manager.py` | 7 unit tests | 89 |
| `tests/test_dock_bar.py` | 7 unit tests | 66 |
| `tests/test_signal_overlay.py` | 6 unit tests | 52 |
| `tests/test_focus_manager.py` | 12 unit tests | 105 |

### Modified Shared Files (4)

| File | Changes |
|------|---------|
| `pyprobe/plots/waveform_plot.py` (473→640 lines) | Added imports for `AxisController`, `PinIndicator`, `EditableAxisItem`, `AxisEditor`, `QColor`, `QPoint`. `__init__` now creates `_axis_controller`, `_pin_indicator`, `_axis_editor`, `_overlay_curves` dict. `_configure_plot()` instantiates `AxisController`, connects `pin_state_changed`, creates `PinIndicator`, calls `_setup_editable_axes()`, creates `AxisEditor`. New methods: `_on_pin_state_changed`, `axis_controller` property, `_setup_editable_axes`, `_start_axis_edit`, `_on_axis_value_committed`, `_on_axis_edit_cancelled`, `add_overlay`, `remove_overlay`, `update_overlay`, `resizeEvent`. |
| `pyprobe/gui/probe_panel.py` (460→685 lines) | Added imports: `QMenu`, `pyqtSignal`, `PlotToolbar`, `InteractionMode`, `drag_helpers`. `ProbePanel` now has signals `maximize_requested`, `park_requested`, `overlay_requested`. `__init__` sets `ClickFocus`, `setAcceptDrops(True)`, creates `PlotToolbar`. New methods: `enterEvent`/`leaveEvent` (toolbar hover), `resizeEvent` (toolbar position), `_on_toolbar_mode_changed`, `_on_toolbar_reset`, `mouseDoubleClickEvent` (maximize), `dragEnterEvent`/`dragLeaveEvent`/`dropEvent` (overlay), `_show_drop_highlight`, `focusInEvent`/`focusOutEvent`, `_show_focus_indicator`, `keyPressEvent` (X/Y/R/Escape). Context menu now includes "Park to Bar". `ProbePanelContainer.__init__` creates `LayoutManager` and `FocusManager`. `create_panel` connects `maximize_requested` and registers with `FocusManager`. `remove_panel` unregisters from `FocusManager`. New `keyPressEvent` for Tab navigation. Properties: `layout_manager`, `focus_manager`. |
| `pyprobe/gui/main_window.py` (700→773 lines) | Added `DockBar` import. `_setup_ui` wraps splitter+dock_bar in a vertical layout; `DockBar` at bottom, hidden by default. `_setup_signals` connects `dock_bar.panel_restore_requested`. `_on_probe_requested` connects `panel.park_requested` and `panel.overlay_requested`. New methods: `_on_panel_park_requested` (hides panel, adds to dock bar), `_on_dock_bar_restore` (finds panel by `identity_label` match, shows it, removes from dock bar), `_on_overlay_requested` (stub — logs and shows status). |
| `pyprobe/gui/code_viewer.py` (400→443 lines) | Added `QDrag` import, `encode_anchor_mime` import. `__init__` adds `_drag_start_pos`. `mouseMoveEvent` checks manhattan distance > 10px, calls `_start_drag()`. `mousePressEvent` records `_drag_start_pos`. `leaveEvent` clears `_drag_start_pos`. New methods: `mouseReleaseEvent` (clear drag), `_start_drag` (creates `QDrag` with encoded anchor MIME). |

---

## What Is NOT Done

### Known Incomplete Items

1. **`_on_overlay_requested` in `main_window.py` is a stub.** It logs and shows a status message but does NOT actually route overlay data to the target `WaveformPlot`. Full implementation requires:
   - Knowing *which* `ProbePanel` received the drop (the signal only carries the overlay anchor, not the target panel).
   - Starting a new probe subscription for the overlay anchor.
   - Routing incoming data to `WaveformPlot.update_overlay()`.
   - Assigning a unique color from the palette.

2. **`update_data()` in `WaveformPlot` does not check pin state before autoscale.** When an axis is pinned, autoscale should be skipped for that axis. Currently `AxisController.set_pinned()` calls `enableAutoRange(False)` on the PlotItem directly, which *may* be sufficient if pyqtgraph respects it — but this needs runtime verification. If autoscale still fires, an explicit guard is needed in `_update_1d_data` / `_update_2d_data`.

3. **Parked panels do not receive data updates.** `_on_panel_park_requested` hides the panel and adds to dock bar, but main_window still routes data via `self._probe_panels[anchor].update_data(...)` — since the panel is only hidden (not removed from `_probe_panels`), it *might* still receive updates. However, `DockBar.update_data()` is a no-op (sparkline is P1). Verify that hidden `ProbePanel` widgets still process `update_data()` calls.

4. **Hit-test priority on double-click maximize.** `ProbePanel.mouseDoubleClickEvent` unconditionally emits `maximize_requested`. It does NOT check whether the double-click landed on an axis (which should trigger the axis editor instead) or on a trace. The spec (04-maximize-restore.md) clearly defines priority: axis tick > axis line > trace > background. This needs a proper hit-test guard.

5. **Toolbar mode auto-revert not implemented.** The spec says Pan/Zoom modes should revert to Pointer after the action completes. `PlotToolbar.revert_to_pointer()` exists but nothing calls it after a pan/zoom gesture.

6. **Context menu "Remove Overlay" not implemented.** The spec (06-signal-overlay.md) says overlay signals should be removable via right-click context menu. No such menu item exists yet.

7. **Animation on maximize/restore not implemented.** `LayoutManager` uses show/hide but no `QPropertyAnimation`. The spec calls for 150-200ms smooth transition.

8. **`_setup_editable_axes` replaces axes via `setAxisItems`.** This may lose axis labels set earlier in `_configure_plot` ("Amplitude", "Sample Index") since the new `EditableAxisItem` instances are created fresh. Need to re-set labels after replacing axes, or set them after `_setup_editable_axes` runs. Check runtime.

---

## Gotchas & Likely Failure Points

### 1. Editable Axis Label Loss (HIGH RISK)
`_configure_plot()` sets axis labels ("Amplitude", "Sample Index") via `self._plot_widget.setLabel(...)` **before** `_setup_editable_axes()` replaces the axis items entirely. The new `EditableAxisItem` objects won't have those labels. Fix: move `setLabel` calls to after `_setup_editable_axes()`, or call `setLabel` again at the end.

### 2. `EditableAxisItem.range` attribute (HIGH RISK)
`editable_axis.py` accesses `self.range` in `mouseDoubleClickEvent`. PyQtGraph `AxisItem` exposes range via `self.range` which is a list `[min, max]` — BUT this is only populated after the axis is linked to a ViewBox. If double-clicked before any data is plotted, `self.range` could be `[0, 1]` (default) or `None`, causing unexpected behavior.

### 3. `QGraphicsOpacityEffect` on PlotToolbar (MEDIUM RISK)
`PlotToolbar` uses `QGraphicsOpacityEffect` for fade animation. In Qt, applying a `QGraphicsEffect` to a widget can cause it to be rendered into an offscreen buffer, which may interfere with hover events on child buttons. If toolbar buttons don't respond to clicks when semi-transparent, this is why. Alternative: use stylesheet-based opacity on individual buttons.

### 4. `DockBar` anchor_key matching (MEDIUM RISK)
`_on_dock_bar_restore` iterates `_probe_panels` looking for `anchor.identity_label() == anchor_key`. The `identity_label()` method must return a stable, unique string. If two probes share the same symbol name but different locations, this lookup could match the wrong one. Verify `identity_label()` includes enough uniqueness (file:line:col).

### 5. Drag initiation on CodeViewer (MEDIUM RISK)
`mousePressEvent` simultaneously emits `probe_requested`/`probe_removed` AND records `_drag_start_pos`. This means a click-to-probe action will also start tracking for a drag. If the user clicks and moves slightly (< 10px), the probe toggles. If >= 10px, a drag starts AND the probe already toggled. This may cause confusing behavior — the user drags a symbol but it also gets probed. Consider: only track drag for already-active probes, or suppress the probe signal if a drag starts.

### 6. `ProbePanel` stylesheet conflicts (LOW-MEDIUM RISK)
Three different methods set the ProbePanel stylesheet: `_setup_ui` (default), `_show_drop_highlight`, and `_show_focus_indicator`. Each replaces the entire stylesheet. If focus indicator is active and a drag enters, the drop highlight will overwrite the focus indicator. When drag leaves, `_show_drop_highlight(False)` restores `_focus_style_base` (the unfocused style), erasing the focus indicator even though the panel still has focus.

### 7. `AxisController` inherits from `QObject` (LOW RISK)
`AxisController.__init__` calls `super().__init__()` without a parent. This means it's not parented to the plot widget and could be garbage-collected. In practice, `WaveformPlot._axis_controller` holds a strong reference so it should survive, but if WaveformPlot is ever GC'd without explicit cleanup, the signal connections may dangle.

### 8. SVG icons may not render (LOW RISK)
The SVG icons were created by a subagent and are minimal (~4-10 lines each). They may not render correctly in `QIcon` if the SVG structure is malformed. `PlotToolbar` has text fallbacks (`mode.name[0]`) so the toolbar will still function, just with letter labels instead of icons.

---

## Test Files vs Runtime

All 7 test files were created by subagents. They import from `pyprobe.*` and construct widgets. **None have been run.** They likely need:
- A `QApplication` instance (already handled in some via `@pytest.fixture`)
- PyQt6 and pyqtgraph installed
- Some tests mock `PlotItem` / `ViewBox` which may break if the mock doesn't implement `getViewBox()` correctly

Run with: `pytest tests/test_axis_controller.py tests/test_axis_editor.py tests/test_plot_toolbar.py tests/test_layout_manager.py tests/test_dock_bar.py tests/test_signal_overlay.py tests/test_focus_manager.py -v`

---

## File Dependency Graph

```
code_viewer.py ──drag──> drag_helpers.py ──mime──> probe_panel.py (drop target)
                                                        │
                                    ┌───────────────────┼───────────────────┐
                                    ▼                   ▼                   ▼
                            plot_toolbar.py     layout_manager.py    focus_manager.py
                                    │
                                    ▼
                            waveform_plot.py
                            ├── axis_controller.py
                            ├── pin_indicator.py
                            ├── editable_axis.py
                            └── axis_editor.py

main_window.py
├── dock_bar.py (bottom bar)
├── probe_panel.py (park_requested, overlay_requested signals)
└── code_viewer.py (drag initiation)
```

---

## Recommended Next Steps

1. **Run the app** (`python -m pyprobe <some_script.py>`) and visually verify:
   - Toolbar appears on hover (max 40% opacity)
   - Lock icons appear after zoom/pan
   - Double-click axis tick opens inline editor
   - Keyboard shortcuts X/Y/R/Escape/Tab work
   - Park to Bar via context menu
   - Restore from dock bar

2. **Run tests** and fix failures.

3. **Fix the high-risk items** listed above (especially axis label loss and hit-test priority on double-click).

4. **Complete the overlay stub** in `main_window.py` — connect `overlay_requested` to actual data routing.

5. **Add mode auto-revert** — connect ViewBox mouse release to `PlotToolbar.revert_to_pointer()`.

6. **Fix stylesheet state conflicts** in `ProbePanel` — use a state-based approach that composes border styles rather than replacing the entire stylesheet.
