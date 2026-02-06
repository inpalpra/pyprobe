# Plan 2: Lens UI Components

**Focus:** Build the lens dropdown widget and integrate it into probe panel header.

**Branch:** `m2/lens-ui`

**Dependencies:** Plan 0 (PluginRegistry)

**Complexity:** Medium (M)

---

## Overview

Add a lens dropdown to the probe panel header that allows users to switch visualization modes without re-probing. The dropdown is the **primary** access method (per M2 UX spec). Context menu is **secondary** (for discoverability only).

```
┌─────────────────────────────────────────────────────────────────┐
│ rx_symbols @ main.py:42     [●] [Constellation ▾]              │
│                              ↑        ↑                        │
│                          state    lens dropdown                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Files to Create

### `pyprobe/gui/lens_dropdown.py`
```python
"""Lens dropdown widget for switching visualization plugins."""
from typing import List, Optional, Callable
from PyQt6.QtWidgets import QComboBox, QWidget
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor

from ..plugins import PluginRegistry, ProbePlugin
from ..logging import get_logger

logger = get_logger(__name__)


class LensDropdown(QComboBox):
    """Dropdown for selecting visualization lens.
    
    Shows all plugins that can handle the current data type.
    Incompatible plugins are shown but disabled.
    
    Signals:
        lens_changed: Emitted when user selects a different lens.
                      Args: (plugin_name: str)
    """
    
    lens_changed = pyqtSignal(str)  # plugin name
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_dtype: Optional[str] = None
        self._current_shape: Optional[tuple] = None
        self._compatible_plugins: List[ProbePlugin] = []
        
        self._setup_style()
        self.currentIndexChanged.connect(self._on_selection_changed)
    
    def _setup_style(self):
        """Apply dark cyberpunk styling."""
        self.setStyleSheet("""
            QComboBox {
                background-color: #1a1a2e;
                color: #00ffff;
                border: 1px solid #00ffff;
                border-radius: 3px;
                padding: 2px 20px 2px 8px;
                min-width: 100px;
                font-family: 'JetBrains Mono';
                font-size: 10px;
            }
            QComboBox:hover {
                border-color: #ff00ff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #00ffff;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a2e;
                color: #00ffff;
                selection-background-color: #00ffff;
                selection-color: #1a1a2e;
                border: 1px solid #00ffff;
            }
            QComboBox QAbstractItemView::item:disabled {
                color: #555555;
            }
        """)
    
    def update_for_dtype(self, dtype: str, shape: Optional[tuple] = None) -> None:
        """Update dropdown items based on data type.
        
        Compatible plugins are enabled, incompatible are disabled (shown grayed).
        UX principle: Discovery beats documentation - show what's possible.
        """
        self._current_dtype = dtype
        self._current_shape = shape
        
        registry = PluginRegistry.instance()
        all_plugins = registry.all_plugins
        self._compatible_plugins = registry.get_compatible_plugins(dtype, shape)
        
        # Block signals during update
        self.blockSignals(True)
        self.clear()
        
        for plugin in all_plugins:
            self.addItem(plugin.name)
            index = self.count() - 1
            
            # Disable incompatible plugins
            if plugin not in self._compatible_plugins:
                model = self.model()
                item = model.item(index)
                item.setEnabled(False)
        
        # Select default (highest priority compatible)
        if self._compatible_plugins:
            default_name = self._compatible_plugins[0].name
            self.setCurrentText(default_name)
        
        self.blockSignals(False)
        logger.debug(f"Lens dropdown updated for {dtype}: {len(self._compatible_plugins)} compatible")
    
    def set_lens(self, plugin_name: str) -> bool:
        """Programmatically set the current lens.
        
        Returns True if successful, False if plugin is incompatible.
        """
        registry = PluginRegistry.instance()
        plugin = registry.get_plugin_by_name(plugin_name)
        
        if plugin and plugin in self._compatible_plugins:
            self.setCurrentText(plugin_name)
            return True
        return False
    
    def current_plugin(self) -> Optional[ProbePlugin]:
        """Get the currently selected plugin."""
        name = self.currentText()
        return PluginRegistry.instance().get_plugin_by_name(name)
    
    def _on_selection_changed(self, index: int) -> None:
        """Handle user changing the lens selection."""
        plugin_name = self.currentText()
        plugin = PluginRegistry.instance().get_plugin_by_name(plugin_name)
        
        # Only emit if it's a compatible plugin
        if plugin and plugin in self._compatible_plugins:
            logger.debug(f"Lens changed to: {plugin_name}")
            self.lens_changed.emit(plugin_name)
```

---

## Files to Modify

### `pyprobe/gui/probe_panel.py`

Add lens dropdown to `ProbePanel.__init__` and `_setup_ui`:

```python
# In imports:
from .lens_dropdown import LensDropdown

# In ProbePanel._setup_ui (header section):
def _setup_ui(self):
    # ... existing header layout code ...
    
    # Add lens dropdown to header (before or after state indicator)
    self._lens_dropdown = LensDropdown()
    self._lens_dropdown.update_for_dtype(self._dtype)
    self._lens_dropdown.lens_changed.connect(self._on_lens_changed)
    header.addWidget(self._lens_dropdown)
    
    # ... rest of existing code ...

# Add new method:
def _on_lens_changed(self, plugin_name: str):
    """Handle lens change - swap out the plot widget."""
    from ..plugins import PluginRegistry
    
    registry = PluginRegistry.instance()
    plugin = registry.get_plugin_by_name(plugin_name)
    
    if not plugin:
        return
    
    # Remember current data for new widget
    current_value = getattr(self._plot, '_data', None) if self._plot else None
    
    # Remove old plot widget
    if self._plot:
        self._plot.setParent(None)
        self._plot.deleteLater()
    
    # Create new widget from plugin
    self._current_plugin = plugin
    self._plot = plugin.create_widget(self._anchor.symbol, self._color, self)
    
    # Insert into layout (after header, before stats if any)
    self.layout().insertWidget(1, self._plot)
    
    # Re-apply data if we had any
    if current_value is not None:
        plugin.update(self._plot, current_value, self._dtype, self._shape)

def update_data(self, value, dtype: str, shape=None, source_info: str = ""):
    """Update via plugin system."""
    self._dtype = dtype
    self._shape = shape
    self._data = value
    
    # Update dropdown if dtype changed
    if self._lens_dropdown:
        self._lens_dropdown.update_for_dtype(dtype, shape)
    
    # Update via current plugin
    if self._current_plugin and self._plot:
        self._current_plugin.update(self._plot, value, dtype, shape, source_info)

# Add property:
@property
def current_lens(self) -> str:
    """Get current lens name."""
    return self._lens_dropdown.currentText() if self._lens_dropdown else ""
```

---

## Context Menu (Secondary Access)

Add to `ProbePanel`:

```python
from PyQt6.QtWidgets import QMenu
from PyQt6.QtCore import Qt

def contextMenuEvent(self, event):
    """Show context menu with View As... option."""
    menu = QMenu(self)
    menu.setStyleSheet("""
        QMenu {
            background-color: #1a1a2e;
            color: #00ffff;
            border: 1px solid #00ffff;
        }
        QMenu::item:selected {
            background-color: #00ffff;
            color: #1a1a2e;
        }
        QMenu::item:disabled {
            color: #555555;
        }
    """)
    
    view_menu = menu.addMenu("View As...")
    
    from ..plugins import PluginRegistry
    registry = PluginRegistry.instance()
    compatible = registry.get_compatible_plugins(self._dtype, self._shape)
    
    for plugin in registry.all_plugins:
        action = view_menu.addAction(plugin.name)
        action.setCheckable(True)
        action.setChecked(plugin.name == self.current_lens)
        action.setEnabled(plugin in compatible)
        action.triggered.connect(lambda checked, name=plugin.name: self._lens_dropdown.set_lens(name))
    
    menu.exec(event.globalPos())
```

---

## Verification

```bash
# Manual test:
source .venv/bin/activate && python -m pyprobe examples/dsp_demo.py

# Steps:
# 1. Click on a complex array variable → constellation appears
# 2. Click lens dropdown → see "Constellation" selected, "I/Q Split", "Spectrum" enabled
# 3. Select "I/Q Split" → widget swaps, data preserved
# 4. Right-click panel → "View As..." menu shows same options
# 5. Probing a scalar → dropdown shows "History", "Value"
# 6. "Waveform" should be grayed/disabled for scalar
```

---

## Merge Conflict Risk

**Low** - Creates new file `lens_dropdown.py`, modifies only `probe_panel.py`.
