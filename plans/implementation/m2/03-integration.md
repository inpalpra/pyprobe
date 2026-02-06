# Plan 3: Integration

**Focus:** Wire plugin system into main window and ensure data flows correctly through new architecture.

**Branch:** `m2/integration`

**Dependencies:** Plan 0, Plan 1, Plan 2 (run last)

**Complexity:** Medium (M)

---

## Overview

This plan connects all M2 components:
1. `ProbePanel` creates widgets via plugins instead of `plot_factory`
2. `MainWindow` tracks lens choice per probe
3. Data flows: Tracer → IPC → MainWindow → Plugin.update()
4. Lens state persists across data updates

---

## Files to Modify

### `pyprobe/gui/probe_panel.py`

**Changes:**
1. Replace `plot_factory.create_plot()` with `PluginRegistry.get_default_plugin()`
2. Store `_current_plugin` reference
3. Store `_current_lens` name in probe state

```python
# In __init__:
def __init__(self, anchor: ProbeAnchor, color: QColor, dtype: str, parent=None):
    super().__init__(parent)
    self._anchor = anchor
    self._color = color
    self._dtype = dtype
    self._shape = None
    self._data = None
    
    # Plugin system (M2)
    from ..plugins import PluginRegistry
    self._registry = PluginRegistry.instance()
    self._current_plugin = self._registry.get_default_plugin(dtype)
    self._current_lens_name = self._current_plugin.name if self._current_plugin else "Unknown"
    
    self._setup_ui()

# In _setup_ui, replace create_plot() call:
def _setup_ui(self):
    # ... existing layout code ...
    
    # Create plot widget using plugin system
    if self._current_plugin:
        self._plot = self._current_plugin.create_widget(
            self._anchor.symbol, 
            self._color, 
            self
        )
    else:
        # Fallback: placeholder widget
        self._plot = QLabel("No plugin for this data type")
        self._plot.setStyleSheet("color: #ff0000;")
    
    layout.addWidget(self._plot)
    # ... rest of existing code ...
```

### `pyprobe/gui/main_window.py`

**Changes:**
1. Track lens choice per anchor in probe state
2. Pass lens info when creating panels
3. Preserve lens on data updates

```python
# Add to MainWindow class:

def _on_probe_requested(self, anchor: ProbeAnchor):
    """Handle new probe request."""
    # ... existing probe creation code ...
    
    # Track probe metadata including lens
    self._probe_metadata[anchor] = {
        'lens': None,  # Will be set to default by panel
        'dtype': None,
    }
    
    # Create panel as before
    panel = self._probe_panel_container.create_probe_panel(anchor, color)
    
    # Connect lens change signal
    if hasattr(panel, '_lens_dropdown'):
        panel._lens_dropdown.lens_changed.connect(
            lambda name, a=anchor: self._on_lens_changed(a, name)
        )

def _on_lens_changed(self, anchor: ProbeAnchor, lens_name: str):
    """Remember lens choice for this probe."""
    if anchor in self._probe_metadata:
        self._probe_metadata[anchor]['lens'] = lens_name
        logger.debug(f"Lens changed for {anchor.short_label()}: {lens_name}")

def _handle_probe_data(self, msg: Message):
    """Handle incoming probe data."""
    # ... existing data handling ...
    
    panel = self._probe_panel_container.get_panel(anchor=anchor)
    if panel:
        # Update data through panel (which uses plugin.update())
        panel.update_data(value, dtype, shape, source_info)
        
        # Track dtype for metadata
        if anchor in self._probe_metadata:
            self._probe_metadata[anchor]['dtype'] = dtype
```

### `pyprobe/gui/probe_panel.py` - `ProbePanelContainer`

**Changes:**
Update factory method to use plugins:

```python
def create_probe_panel(self, anchor: ProbeAnchor, color: QColor) -> ProbePanel:
    """Create a probe panel for an anchor (M2 plugin-aware)."""
    # Initial dtype is unknown - will be set on first data
    dtype = "unknown"
    
    panel = ProbePanel(anchor, color, dtype, self._content)
    self._panels[anchor] = panel
    
    # Add to grid layout
    # ... existing layout code ...
    
    return panel
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         TraceR (Runner)                         │
│   captures value at anchor → sends via IPC                      │
└─────────────────────────────────────────┬───────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MainWindow (GUI)                           │
│   _handle_probe_data(msg)                                       │
│   1. Extract anchor, value, dtype, shape                        │
│   2. Find panel for anchor                                      │
│   3. Call panel.update_data(...)                                │
└─────────────────────────────────────────┬───────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ProbePanel                                  │
│   update_data(value, dtype, shape, source_info)                 │
│   1. Update lens dropdown for dtype                             │
│   2. Call self._current_plugin.update(widget, value, ...)       │
└─────────────────────────────────────────┬───────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ProbePlugin                                 │
│   update(widget, value, dtype, shape, source_info)              │
│   → Renders data in widget                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Migration Path

### Phase 1: Coexistence
- Keep old `plot_factory.py` working
- `ProbePanel` checks for plugin system first, falls back to factory

```python
def _create_plot_widget(self):
    """Create plot using plugin system with factory fallback."""
    from ..plugins import PluginRegistry
    
    registry = PluginRegistry.instance()
    plugin = registry.get_default_plugin(self._dtype)
    
    if plugin:
        self._current_plugin = plugin
        return plugin.create_widget(self._anchor.symbol, self._color, self)
    else:
        # Fallback to old factory (deprecated)
        from ..plots.plot_factory import create_plot
        return create_plot(self._anchor.symbol, self._dtype, self)
```

### Phase 2: Cleanup (post-M2)
- Remove `plot_factory.py`
- Remove `base_plot.py`
- Update all references

---

## Verification

### Automated Test

```python
# tests/test_plugin_integration.py
import pytest
from PyQt6.QtWidgets import QApplication
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.gui.probe_panel import ProbePanel
from pyprobe.plugins import PluginRegistry
from PyQt6.QtGui import QColor

@pytest.fixture
def app():
    return QApplication([])

def test_panel_uses_plugin(app):
    """ProbePanel should use plugin system."""
    anchor = ProbeAnchor("/test.py", 10, 0, "x", "main")
    panel = ProbePanel(anchor, QColor("#00ffff"), "array_1d")
    
    assert panel._current_plugin is not None
    assert panel._current_plugin.name == "Waveform"

def test_lens_switch_preserves_data(app):
    """Switching lens should preserve probe data."""
    anchor = ProbeAnchor("/test.py", 10, 0, "x", "main")
    panel = ProbePanel(anchor, QColor("#00ffff"), "array_complex")
    
    # Update with data
    import numpy as np
    data = np.array([1+1j, 2+2j, 3+3j])
    panel.update_data(data, "array_complex", (3,))
    
    # Switch lens
    panel._lens_dropdown.set_lens("Spectrum")
    
    # Data should still be available
    assert panel._data is not None
```

### Manual Test

```bash
source .venv/bin/activate && python -m pyprobe examples/dsp_demo.py

# Full M2 verification:
# 1. Probe a 1D array → Waveform appears
# 2. Click dropdown → see "Waveform" (selected), "Spectrum" (enabled)
# 3. Switch to Spectrum → FFT view appears, same data
# 4. Probe a complex array → Constellation appears
# 5. Switch to "I/Q Split" → dual waveform view
# 6. Probe a scalar → History chart appears
# 7. Switch to "Value" → simple number display
# 8. Right-click any panel → "View As..." shows same options
# 9. Remove probe → cleanly removed (no orphan widgets)
# 10. Re-probe same variable → default lens shown again
```

---

## Integration Checklist

- [ ] Plugin system imported in `pyprobe/__init__.py`
- [ ] `ProbePanel` creates widgets via `PluginRegistry.get_default_plugin()`
- [ ] `LensDropdown` appears in probe panel header
- [ ] Lens dropdown updates when dtype changes
- [ ] Switching lens swaps widget without losing data
- [ ] Context menu "View As..." works as secondary access
- [ ] Incompatible lenses are disabled (not hidden)
- [ ] Probe color consistent across all lens types
- [ ] Old `plot_factory.py` still works as fallback
- [ ] No memory leaks when switching lenses

---

## Merge Conflict Risk

**Medium** - Modifies `main_window.py` and `probe_panel.py`. Run after Phase 2 merges.
