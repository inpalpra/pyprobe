# Plan 0: Plugin ABC & Registry

**Focus:** Define the `ProbePlugin` abstract base class and `PluginRegistry` for discovering/selecting plugins.

**Branch:** `m2/plugin-abc`

**Dependencies:** None (this is the foundation)

**Complexity:** Small (S)

---

## Files to Create

### `pyprobe/plugins/__init__.py`
```python
"""Plugin system for visualization lenses."""
from .base import ProbePlugin
from .registry import PluginRegistry

__all__ = ['ProbePlugin', 'PluginRegistry']
```

### `pyprobe/plugins/base.py`
```python
"""Abstract base class for visualization plugins (lenses)."""
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QColor


class ProbePlugin(ABC):
    """Abstract base class for probe visualization plugins.
    
    Each plugin represents a "lens" - a way to view probed data.
    Plugins declare what data types they can handle and provide
    a widget for rendering.
    
    Lifecycle:
    1. PluginRegistry calls can_handle() to check compatibility
    2. ProbePanel calls create_widget() to get the visualization
    3. Data flows via update() calls from IPC
    4. Color is provided for consistent styling
    """
    
    # Human-readable name shown in lens dropdown
    name: str = "Unknown"
    
    # Icon name (optional, for dropdown)
    icon: Optional[str] = None
    
    # Priority for auto-selection (higher = preferred default)
    # When multiple plugins can handle a dtype, highest priority wins
    priority: int = 0
    
    @abstractmethod
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        """Return True if this plugin can visualize the given data type.
        
        Args:
            dtype: Data type string from classifier (e.g., 'array_1d', 'complex')
            shape: Shape tuple if array, None otherwise
            
        Returns:
            True if this plugin can render this data type
        """
        pass
    
    @abstractmethod
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None) -> QWidget:
        """Create and return the visualization widget.
        
        Args:
            var_name: Variable name (for display)
            color: Assigned probe color (use for styling)
            parent: Optional parent widget
            
        Returns:
            QWidget that renders the data
        """
        pass
    
    @abstractmethod
    def update(self, widget: QWidget, value: Any, dtype: str, 
               shape: Optional[Tuple[int, ...]] = None,
               source_info: str = "") -> None:
        """Update the widget with new data.
        
        Args:
            widget: Widget created by create_widget()
            value: The probed value (numpy array, scalar, etc.)
            dtype: Data type string
            shape: Shape if array
            source_info: Source location string (e.g., "func:42")
        """
        pass
```

### `pyprobe/plugins/registry.py`
```python
"""Plugin registry for discovering and selecting visualization plugins."""
from typing import Dict, List, Optional, Tuple, Type
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget

from .base import ProbePlugin
from ..logging import get_logger

logger = get_logger(__name__)


class PluginRegistry:
    """Central registry for all visualization plugins.
    
    Singleton pattern - use PluginRegistry.instance() to get.
    
    Responsibilities:
    - Auto-discover builtin plugins at startup
    - Match (dtype, shape) to compatible plugins
    - Select default plugin for each data type
    - Provide list of available plugins for lens dropdown
    """
    
    _instance: Optional['PluginRegistry'] = None
    
    @classmethod
    def instance(cls) -> 'PluginRegistry':
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._discover_plugins()
        return cls._instance
    
    def __init__(self):
        self._plugins: List[ProbePlugin] = []
    
    def _discover_plugins(self) -> None:
        """Discover and register builtin plugins."""
        # Import here to avoid circular imports
        from .builtins import get_builtin_plugins
        
        for plugin in get_builtin_plugins():
            self.register(plugin)
            logger.debug(f"Registered plugin: {plugin.name}")
    
    def register(self, plugin: ProbePlugin) -> None:
        """Register a plugin instance."""
        self._plugins.append(plugin)
    
    def get_compatible_plugins(self, dtype: str, shape: Optional[Tuple[int, ...]] = None) -> List[ProbePlugin]:
        """Get all plugins that can handle the given data type.
        
        Returns:
            List of compatible plugins, sorted by priority (highest first)
        """
        compatible = [p for p in self._plugins if p.can_handle(dtype, shape)]
        return sorted(compatible, key=lambda p: p.priority, reverse=True)
    
    def get_default_plugin(self, dtype: str, shape: Optional[Tuple[int, ...]] = None) -> Optional[ProbePlugin]:
        """Get the default (highest priority) plugin for a data type.
        
        Returns:
            Best matching plugin, or None if no plugin can handle this type
        """
        compatible = self.get_compatible_plugins(dtype, shape)
        return compatible[0] if compatible else None
    
    def get_plugin_by_name(self, name: str) -> Optional[ProbePlugin]:
        """Get a plugin by its name."""
        for plugin in self._plugins:
            if plugin.name == name:
                return plugin
        return None
    
    @property
    def all_plugins(self) -> List[ProbePlugin]:
        """Get all registered plugins."""
        return list(self._plugins)
```

### `pyprobe/plugins/builtins/__init__.py`
```python
"""Builtin visualization plugins."""
from typing import List
from ..base import ProbePlugin


def get_builtin_plugins() -> List[ProbePlugin]:
    """Return all builtin plugin instances.
    
    Each plugin is instantiated once and reused.
    Order doesn't matter - priority determines default selection.
    """
    # Import here to allow gradual migration
    # Plan 1 will implement these
    from .waveform import WaveformPlugin
    from .constellation import ConstellationPlugin
    from .scalar_history import ScalarHistoryPlugin
    from .scalar_display import ScalarDisplayPlugin
    
    return [
        WaveformPlugin(),
        ConstellationPlugin(),
        ScalarHistoryPlugin(),
        ScalarDisplayPlugin(),
    ]
```

---

## Verification

```bash
# After Plan 1 implements builtins:
python -c "
from pyprobe.plugins import PluginRegistry
reg = PluginRegistry.instance()
print(f'Plugins registered: {len(reg.all_plugins)}')
for p in reg.all_plugins:
    print(f'  - {p.name} (priority={p.priority})')
"
# Should print all builtin plugins
```

---

## Interface Contract

Plugins MUST:
1. Be stateless (widget holds state, plugin creates/updates widgets)
2. Handle missing data gracefully (value=None → show placeholder)
3. Use provided `color` parameter for primary styling
4. Not modify any global state

Plugins SHOULD:
1. Provide meaningful feedback when data is incompatible
2. Handle array size changes without error
3. Use consistent font/styling from theme

---

## Merge Conflict Risk

**None** - Only creates new files.
