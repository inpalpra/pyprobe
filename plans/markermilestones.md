# Marker System — Milestone Plan

Keysight PXA-style markers for PyProbe graphs. Markers snap to traces, display values in a top-right overlay, and can be managed via Alt+Click, context menu, and a floating manager dialog.

**Key design decisions:**
- Relative markers move when reference marker moves (position = ref_x + delta_x)
- Marker shapes auto-cycle per ID: m0=diamond, m1=triangle-up, m2=square, m3=cross, m4=circle, m5=star, then repeat
- Users can change shape and color in the marker manager

---

## M1 — Data Model (`MarkerStore`)

**Goal:** Build the core data model with no visual dependencies.

**Files:**
- **[NEW]** `pyprobe/plots/marker_model.py`
- **[NEW]** `tests/plots/test_marker_model.py`

**Deliverables:**
1. `MarkerType` enum: `ABSOLUTE`, `RELATIVE`
2. `MarkerShape` enum: `DIAMOND`, `TRIANGLE_UP`, `SQUARE`, `CROSS`, `CIRCLE`, `STAR`
3. `MarkerData` dataclass:
   - `id: str` (m0, m1, …)
   - `x: float`, `y: float`
   - `trace_key` (which curve — int for WaveformWidget, str for ComplexWidget)
   - `marker_type: MarkerType` (default ABSOLUTE)
   - `ref_marker_id: Optional[str]` (required if RELATIVE)
   - `label: str` (defaults to id)
   - `shape: MarkerShape` (auto-cycled from id index)
   - `color: str` (hex color, default '#ffffff')
4. `MarkerStore(QObject)`:
   - `add_marker(trace_key, x, y) → MarkerData`
   - `remove_marker(marker_id: str)`
   - `update_marker(marker_id, **kwargs)`
   - `get_markers() → list[MarkerData]`
   - `get_marker(marker_id) → MarkerData`
   - `get_next_id() → str`
   - `get_display_values(marker_id) → (x_display, y_display)` — resolves relative deltas
   - Signal: `markers_changed = pyqtSignal()`
   - Relative position: when ref moves, relative marker's absolute position = ref.x + stored_delta_x

**Verification:**
```bash
./.venv/bin/python -m pytest tests/plots/test_marker_model.py -v
```
- add/remove/update markers
- auto-increment IDs (m0, m1, m2)
- relative marker delta computation
- signal emission on changes

---

## M2 — Visual Items (Glyphs + Overlay)

**Goal:** Draw markers on graphs and show values in a top-right overlay.

**Files:**
- **[NEW]** `pyprobe/plots/marker_items.py`

**Deliverables:**

### MarkerGlyph
- Thin wrapper around `pg.ScatterPlotItem` for a single marker
- Maps `MarkerShape` → pyqtgraph symbol (`'d'`, `'t'`, `'s'`, `'+'`, `'o'`, `'star'`)
- Fixed pixel size (~12px), does not scale with zoom
- High Z-value (above curves/grid, Z=100)
- Draws label text next to glyph (e.g., "m0")

### MarkerOverlay
- `QWidget` child of the plot widget, positioned top-right
- Semi-transparent dark background (`rgba(13,13,13,0.85)`)
- Vertical list of marker readouts using `JetBrains Mono 9pt`:
  ```
  m0: X=1.234k  Y=45.67m
  m1: X=2.100k  Y=12.34m
  Δm2→m0: ΔX=866.0  ΔY=-33.33m
  ```
- `raise_()` called after every refresh to stay on top of everything
- Alt+Click on a marker entry removes that marker

### Snap-to-Trace Helper
- `snap_to_nearest(plot_widget, curves, scene_pos) → (trace_key, x, y)`
- For each visible curve, find closest data point in X
- Among candidates, pick the one closest in Y to click position
- Uses `curve.getData()` API

**Verification:**
- Visual inspection: create widget, add markers, verify glyphs and overlay render

---

## M3 — Widget Integration

**Goal:** Wire MarkerStore + visual items into all graph widgets.

**Files:**
- **[MODIFY]** `pyprobe/plugins/builtins/waveform.py` — `WaveformWidget`
- **[MODIFY]** `pyprobe/plugins/builtins/complex_plots.py` — `ComplexWidget` (base class)
- **[MODIFY]** `pyprobe/plugins/builtins/constellation.py` — `ConstellationWidget`

**Changes per widget:**

1. In `_configure_plot()`:
   - Create `self._marker_store = MarkerStore()`
   - Create `self._marker_overlay = MarkerOverlay(self._plot_widget)`
   - Connect `_marker_store.markers_changed` → `_refresh_markers()`

2. New method `_on_alt_click(ev)`:
   - Check for Alt modifier
   - Call `snap_to_nearest()` to find closest trace point
   - Call `_marker_store.add_marker(trace_key, x, y)`

3. New method `_refresh_markers()`:
   - Clear old `MarkerGlyph` items from plot
   - For each marker in store, create `MarkerGlyph` at (x, y)
   - Update `MarkerOverlay` text entries
   - Call `_marker_overlay.raise_()` for z-order

4. On `resizeEvent`: reposition `MarkerOverlay` to top-right

5. After curve data updates: call `_refresh_markers()` to re-snap markers

**Dimension info migration:**
- Remove `[(500,)]` bracket notation from `_info_label`
- Add dimension/shape info to stats area (bottom-left) instead

**Verification:**
```bash
QT_QPA_PLATFORM=offscreen ./.venv/bin/python -m pytest tests/gui/test_markers_gui.py -v
```
- Create WaveformWidget, feed data, call `add_marker()`, verify glyph count
- Verify overlay text updates
- Remove marker, verify cleanup

---

## M4 — Context Menu & Manager Dialog

**Goal:** Right-click menu integration and floating marker manager.

**Files:**
- **[NEW]** `pyprobe/gui/marker_manager.py`
- **[MODIFY]** `pyprobe/gui/probe_panel.py`

### Marker Manager Dialog
A non-modal `QDialog` with a `QTableWidget`:

| Column | Widget | Notes |
|--------|--------|-------|
| ID | QLabel | Read-only (m0, m1, …) |
| Label | QLineEdit | Editable, defaults to ID |
| X | QDoubleSpinBox | Editable, snaps to nearest trace point |
| Y | QLabel | Read-only, auto-computed |
| Trace | QComboBox | Available curves |
| Type | QComboBox | Absolute / Relative |
| Ref | QComboBox | Reference marker (enabled only if Relative) |
| Shape | QComboBox | Diamond, Triangle, Square, Cross, Circle, Star |
| Color | QPushButton | Color picker |
| Delete | QPushButton | Remove row |

- "Add Marker" button at bottom
- Changes apply immediately to MarkerStore
- Themed to match PyProbe dark theme

### ProbePanel Context Menu
In `contextMenuEvent()`, add after "Change Color…":
```
─── separator ───
Markers ▸
    Add Marker at Center
    ──────
    Marker Manager…
    ──────
    Clear All Markers
```

**Verification:**
- Open context menu, verify "Markers" submenu exists
- Click "Marker Manager…", verify dialog opens
- Add/edit/delete markers in dialog, verify plot updates

---

## M5 — Polish & Edge Cases

**Goal:** Handle edge cases, theme integration, and final polish.

**Deliverables:**
1. **Theme support**: marker overlay background and text colors from theme
2. **Lens switching**: preserve markers when switching lenses (e.g., Waveform → FFT)
   - MarkerStore lives on ProbePanel level, or markers are cleared on lens change with user confirmation
3. **Zoom/pan**: markers stay at correct data coordinates during zoom/pan
4. **Multi-curve markers**: ensure markers work on overlaid traces (drag-drop overlays)
5. **Marker persistence**: markers survive data updates (re-snap Y to new data at same X)
6. **Keyboard**: Consider adding keyboard shortcut (e.g., `N` for next marker, `Delete` to remove focused marker)

**Verification:**
- Full manual test: zoom/pan with markers, switch lenses, theme changes
- Run existing test suite to verify no regressions:
```bash
./.venv/bin/python -m pytest tests/ -v --timeout=30
```
