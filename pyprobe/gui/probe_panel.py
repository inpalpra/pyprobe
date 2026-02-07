"""
Container widget for probe panels with flow layout.
"""

from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from pyprobe.logging import get_logger
logger = get_logger(__name__)

from ..core.anchor import ProbeAnchor
from ..plots.base_plot import BasePlot
from ..plots.plot_factory import create_plot
from .probe_state import ProbeState
from .probe_state_indicator import ProbeStateIndicator
from .animations import ProbeAnimations
from .lens_dropdown import LensDropdown


class ProbePanel(QFrame):
    """
    Container for a single probe (plot widget).

    Provides a bordered frame around the plot with consistent sizing,
    state indicator, identity label, and animation support.
    """

    def __init__(
        self,
        anchor: ProbeAnchor,
        color: QColor,
        dtype: str,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._anchor = anchor
        self._color = color
        self._dtype = dtype
        self._plot: Optional[BasePlot] = None
        self._current_plugin: Optional['ProbePlugin'] = None
        self._removal_animation = None
        self._layout: Optional[QVBoxLayout] = None
        self._lens_dropdown: Optional[LensDropdown] = None

        self._setup_ui()

    def _setup_ui(self):
        """Create the panel UI."""
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setStyleSheet("""
            ProbePanel {
                border: 1px solid #333333;
                border-radius: 6px;
                background-color: #0d0d0d;
            }
            ProbePanel:hover {
                border-color: #00ffff;
            }
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(4)

        # Header row with state indicator, identity label, and throttle indicator
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        # State indicator (16x16 pulsing/solid circle)
        self._state_indicator = ProbeStateIndicator()
        header.addWidget(self._state_indicator)

        # Identity label with colored styling
        self._identity_label = QLabel(self._anchor.identity_label())
        color_hex = self._color.name()
        self._identity_label.setStyleSheet(f"""
            QLabel {{
                color: {color_hex};
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        header.addWidget(self._identity_label)

        # Add lens dropdown to header
        self._lens_dropdown = LensDropdown()
        self._lens_dropdown.update_for_dtype(self._dtype)
        self._lens_dropdown.lens_changed.connect(self._on_lens_changed)
        header.addWidget(self._lens_dropdown)

        # Spacer
        header.addStretch()

        # Throttle indicator (hidden by default)
        self._throttle_label = QLabel("\u26a1")  # Lightning bolt
        self._throttle_label.setStyleSheet("""
            QLabel {
                color: #ffff00;
                font-size: 12px;
            }
        """)
        self._throttle_label.setToolTip("Data throttling active")
        self._throttle_label.hide()
        header.addWidget(self._throttle_label)

        self._layout.addLayout(header)

        # Create the appropriate plot widget
        from ..plugins import PluginRegistry
        registry = PluginRegistry.instance()
        
        # Try to find a plugin for this dtype
        plugin = registry.get_default_plugin(self._dtype)
        
        if plugin:
            self._current_plugin = plugin
            self._plot = plugin.create_widget(self._anchor.symbol, self._color, self)
            if self._lens_dropdown:
                 # Update dropdown to match if possible, though update_for_dtype usually handles this
                 pass 
        else:
            # Fallback to legacy factory if no plugin (e.g. unknown dtype or not yet ported)
            # This ensures we don't break if M2 is partial
            self._plot = create_plot(self._anchor.symbol, self._dtype, self)

        self._layout.addWidget(self._plot)

        # Set minimum size
        self.setMinimumSize(300, 250)

    def update_data(self, value, dtype: str, shape=None, source_info: str = ""):
        """Update the plot with new data."""
        prev_dtype = self._dtype
        self._dtype = dtype
        self._shape = shape
        self._data = value

        # Update dropdown if dtype changed
        if self._lens_dropdown is not None and (prev_dtype != dtype):
            self._lens_dropdown.update_for_dtype(dtype, shape)
            
            # Since signals were blocked in dropdown update, check if we need to switch
            current_lens_name = self._lens_dropdown.currentText()
            
            # If we don't have a plugin, or the current plugin doesn't match the dropdown selection
            if not self._current_plugin or self._current_plugin.name != current_lens_name:
                self._on_lens_changed(current_lens_name)
                # Emit signal so listeners (MainWindow) know about the auto-switch
                self._lens_dropdown.lens_changed.emit(current_lens_name)
                # _on_lens_changed will update the new widget with self._data
                return

        # If we have an active plugin-based widget, update it
        if self._current_plugin and self._plot:
            self._current_plugin.update(self._plot, value, dtype, shape, source_info)
            return

        # FALLBACK (Legacy M1 behavior):
        # If dtype changed from unknown, recreate the plot with correct type
        if prev_dtype == 'unknown' and dtype != 'unknown':
            # Remove old plot
            if self._plot:
                self._layout.removeWidget(self._plot)
                self._plot.deleteLater()
            # Create new plot with correct type
            self._plot = create_plot(self._anchor.symbol, dtype, self)
            self._layout.addWidget(self._plot)

        if self._plot:
            self._plot.update_data(value, dtype, shape, source_info)

    def _on_lens_changed(self, plugin_name: str):
        """Handle lens change - swap out the plot widget."""
        from ..plugins import PluginRegistry
        
        registry = PluginRegistry.instance()
        plugin = registry.get_plugin_by_name(plugin_name)
        
        if not plugin:
            return
        
        # Remember current data for new widget if possible (legacy widgets store it in _data sometimes)
        # But here we have self._data stored in update_data
        
        # Remove old plot widget
        if self._plot:
            self._layout.removeWidget(self._plot)
            self._plot.deleteLater()
        
        # Create new widget from plugin
        self._current_plugin = plugin
        self._plot = plugin.create_widget(self._anchor.symbol, self._color, self)
        
        # Insert into layout (index 1, after header)
        self._layout.insertWidget(1, self._plot)
        
        # Re-apply data if we had any
        if hasattr(self, '_data') and self._data is not None:
             plugin.update(self._plot, self._data, self._dtype, getattr(self, '_shape', None))

    @property
    def current_lens(self) -> str:
        """Get current lens name."""
        return self._lens_dropdown.currentText() if self._lens_dropdown else ""

    def contextMenuEvent(self, event):
        """Show context menu with View As... option."""
        from PyQt6.QtWidgets import QMenu, QWidgetAction
        
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
        compatible = registry.get_compatible_plugins(self._dtype, getattr(self, '_shape', None))
        
        for plugin in registry.all_plugins:
            action = view_menu.addAction(plugin.name)
            action.setCheckable(True)
            action.setChecked(plugin.name == self.current_lens)
            action.setEnabled(plugin in compatible)
            # Use default argument to capture loop variable
            action.triggered.connect(lambda checked, name=plugin.name: self._lens_dropdown.set_lens(name))
        
        menu.exec(event.globalPos())

    def set_state(self, state: ProbeState):
        """Update the state indicator."""
        self._state_indicator.set_state(state)

    def show_throttle_indicator(self, active: bool):
        """Show or hide the throttle icon."""
        if active:
            self._throttle_label.show()
        else:
            self._throttle_label.hide()

    def animate_removal(self, on_complete=None):
        """Fade out using ProbeAnimations, then call on_complete."""
        self._removal_animation = ProbeAnimations.fade_out(
            self, duration_ms=300, on_finished=on_complete
        )
        self._removal_animation.start()

    def show_invalid_click_feedback(self):
        """Flash state indicator red to show invalid click."""
        self._state_indicator.show_invalid_feedback()

    @property
    def anchor(self) -> ProbeAnchor:
        """Return the probe anchor."""
        return self._anchor

    @property
    def var_name(self) -> str:
        """Return variable name (for backwards compatibility)."""
        return self._anchor.symbol


class ProbePanelContainer(QScrollArea):
    """
    Scrollable container for multiple probe panels.

    Uses a grid layout to arrange panels.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._panels: Dict[ProbeAnchor, ProbePanel] = {}
        self._panels_by_name: Dict[str, ProbePanel] = {}  # For legacy access
        self._setup_ui()

    def _setup_ui(self):
        """Create the container UI."""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Content widget
        self._content = QWidget()
        self.setWidget(self._content)

        # Grid layout for panels
        self._layout = QGridLayout(self._content)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)

        # Placeholder label
        self._placeholder = QLabel("Add variables to the watch list to probe them")
        self._placeholder.setStyleSheet("color: #666666; font-size: 14px;")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._placeholder, 0, 0)

        # Track grid position
        self._next_row = 0
        self._next_col = 0
        self._cols = 2  # 2 columns by default

    def create_panel(
        self,
        var_name: str,
        dtype: str,
        anchor: Optional[ProbeAnchor] = None,
        color: Optional[QColor] = None
    ) -> ProbePanel:
        """
        Create a new probe panel for a variable.

        Args:
            var_name: Variable name (used as fallback if no anchor)
            dtype: Data type string
            anchor: ProbeAnchor for the probe location
            color: Assigned color for the probe
        """
        logger.debug(f"create_panel called: var_name={var_name}, anchor={anchor}")
        logger.debug(f"  _panels keys: {list(self._panels.keys())}")
        logger.debug(f"  _panels_by_name keys: {list(self._panels_by_name.keys())}")
        
        # Create anchor if not provided (backwards compatibility)
        if anchor is None:
            anchor = ProbeAnchor(
                file="<unknown>",
                line=0,
                col=0,
                symbol=var_name
            )

        # Use default color if not provided
        if color is None:
            color = QColor('#00ffff')

        if anchor in self._panels:
            logger.debug(f"  Returning existing panel from _panels for anchor")
            return self._panels[anchor]

        # Only check by var_name for legacy code (when no real anchor provided)
        # When a real anchor IS provided, we already checked _panels above and it wasn't found,
        # so we need to create a new panel (even if same var_name exists on different line)
        if anchor.file == "<unknown>" and var_name in self._panels_by_name:
            logger.debug(f"  Returning existing panel from _panels_by_name for var_name={var_name}")
            return self._panels_by_name[var_name]

        # Hide placeholder
        self._placeholder.hide()

        # Create panel
        panel = ProbePanel(anchor, color, dtype, self._content)
        self._panels[anchor] = panel
        # Only add to _panels_by_name for legacy (anchor-less) panels
        if anchor.file == "<unknown>":
            self._panels_by_name[var_name] = panel
        logger.debug(f"  Created new panel, added to both dicts")

        # Add to grid
        self._layout.addWidget(panel, self._next_row, self._next_col)

        # Advance position
        self._next_col += 1
        if self._next_col >= self._cols:
            self._next_col = 0
            self._next_row += 1

        return panel

    def remove_panel(self, var_name: str = None, anchor: ProbeAnchor = None):
        """Remove a probe panel by var_name or anchor."""
        logger.debug(f"remove_panel called: var_name={var_name}, anchor={anchor}")
        logger.debug(f"  Before: _panels keys: {list(self._panels.keys())}")
        logger.debug(f"  Before: _panels_by_name keys: {list(self._panels_by_name.keys())}")
        
        panel = None

        if anchor is not None and anchor in self._panels:
            panel = self._panels.pop(anchor)
            logger.debug(f"  Popped panel from _panels for anchor")
            # Remove from name index too
            found_name = None
            for name, p in list(self._panels_by_name.items()):
                if p is panel:
                    found_name = name
                    del self._panels_by_name[name]
                    logger.debug(f"  Also removed from _panels_by_name: {name}")
                    break
            if found_name is None:
                logger.debug(f"  WARNING: Panel not found in _panels_by_name!")
        elif var_name is not None and var_name in self._panels_by_name:
            panel = self._panels_by_name.pop(var_name)
            logger.debug(f"  Popped panel from _panels_by_name for var_name")
            # Remove from anchor index too
            for a, p in list(self._panels.items()):
                if p is panel:
                    del self._panels[a]
                    logger.debug(f"  Also removed from _panels: {a}")
                    break

        if panel is None:
            logger.debug(f"  No panel found to remove")
            return

        logger.debug(f"  After: _panels keys: {list(self._panels.keys())}")
        logger.debug(f"  After: _panels_by_name keys: {list(self._panels_by_name.keys())}")
        
        self._layout.removeWidget(panel)
        panel.deleteLater()

        # Re-layout remaining panels
        self._relayout_panels()

        # Show placeholder if empty
        if not self._panels:
            self._placeholder.show()

    def _relayout_panels(self):
        """Re-layout panels after removal."""
        # Remove all panels from layout
        for panel in self._panels.values():
            self._layout.removeWidget(panel)

        # Re-add in order
        self._next_row = 0
        self._next_col = 0

        for panel in self._panels.values():
            self._layout.addWidget(panel, self._next_row, self._next_col)
            self._next_col += 1
            if self._next_col >= self._cols:
                self._next_col = 0
                self._next_row += 1

    def get_panel(self, var_name: str = None, anchor: ProbeAnchor = None) -> Optional[ProbePanel]:
        """Get a panel by variable name or anchor."""
        if anchor is not None:
            return self._panels.get(anchor)
        if var_name is not None:
            return self._panels_by_name.get(var_name)
        return None

    # === M1 CONVENIENCE METHODS ===

    def create_probe_panel(self, anchor: ProbeAnchor, color: QColor) -> ProbePanel:
        """Create a probe panel for an anchor (M1 API)."""
        return self.create_panel(
            var_name=anchor.symbol,
            dtype='unknown',
            anchor=anchor,
            color=color
        )

    def remove_probe_panel(self, anchor: ProbeAnchor):
        """Remove a probe panel by anchor (M1 API)."""
        self.remove_panel(anchor=anchor)
