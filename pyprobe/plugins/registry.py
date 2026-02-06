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
