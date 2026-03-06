"""Lens dropdown widget for switching visualization plugins."""
from typing import List, Optional, Callable
from PyQt6.QtWidgets import QComboBox, QWidget
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor

from ..plugins import PluginRegistry, ProbePlugin
from pyprobe.logging import get_logger

logger = get_logger(__name__)


def _build_lens_stylesheet(c: dict) -> str:
    return f"""
        QComboBox {{
            background-color: {c['bg_dark']};
            color: {c['accent_primary']};
            border: 1px solid {c['accent_primary']};
            border-radius: 3px;
            padding: 2px 20px 2px 8px;
            min-width: 100px;
            font-family: 'JetBrains Mono';
            font-size: 10px;
        }}
        QComboBox:hover {{
            border-color: {c['accent_secondary']};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid {c['accent_primary']};
            margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {c['bg_dark']};
            color: {c['accent_primary']};
            selection-background-color: {c['accent_primary']};
            selection-color: {c['bg_darkest']};
            border: 1px solid {c['accent_primary']};
        }}
        QComboBox QAbstractItemView::item:disabled {{
            color: {c['text_muted']};
        }}
    """


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

        from pyprobe.gui.theme.theme_manager import ThemeManager
        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.current)
        self.currentIndexChanged.connect(self._on_selection_changed)

    def _apply_theme(self, theme) -> None:
        """Rebuild stylesheet from current theme colors."""
        self.setStyleSheet(_build_lens_stylesheet(theme.colors))
    
    def update_for_dtype(self, dtype: str, shape: Optional[tuple] = None) -> None:
        """Update dropdown items based on data type.
        
        Compatible plugins are enabled, incompatible are disabled (shown grayed).
        UX principle: Discovery beats documentation - show what's possible.
        """
        # Avoid redundant updates
        if self._current_dtype == dtype and self._current_shape == shape:
            return

        self._current_dtype = dtype
        self._current_shape = shape
        
        registry = PluginRegistry.instance()
        self._compatible_plugins = registry.get_compatible_plugins(dtype, shape)


        
        # Block signals during update to prevent triggering change events
        self.blockSignals(True)
        self.clear()
        
        for plugin in self._compatible_plugins:
            self.addItem(plugin.name)
        
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
        plugin = registry.get_plugin_by_name(plugin_name, self._current_dtype)
        
        if plugin and plugin in self._compatible_plugins:
            self.setCurrentText(plugin_name)
            # Explicitly emit signal to ensure listeners are notified of programmatic change
            self.lens_changed.emit(plugin_name)
            return True
        return False
    
    def current_plugin(self) -> Optional[ProbePlugin]:
        """Get the currently selected plugin."""
        name = self.currentText()
        return PluginRegistry.instance().get_plugin_by_name(name, self._current_dtype)
    
    def _on_selection_changed(self, index: int) -> None:
        """Handle user changing the lens selection."""
        plugin_name = self.currentText()
        plugin = PluginRegistry.instance().get_plugin_by_name(plugin_name, self._current_dtype)
        
        # Only emit if it's a compatible plugin
        if plugin and plugin in self._compatible_plugins:
            logger.debug(f"Lens changed to: {plugin_name}")
            self.lens_changed.emit(plugin_name)
        else:
            # If user somehow selected an incompatible plugin (should be disabled), revert?
            # Or just don't emit.
            logger.debug(f"Lens selection '{plugin_name}' ignored (incompatible)")
