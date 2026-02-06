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
