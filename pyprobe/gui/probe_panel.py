"""
Container widget for probe panels with flow layout.
"""

from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel, QMenu,
    QColorDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
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
from .plot_toolbar import PlotToolbar, InteractionMode
from .drag_helpers import has_anchor_mime, decode_anchor_mime
from .probe_buffer import ProbeDataBuffer


class ProbePanel(QFrame):
    """
    Container for a single probe (plot widget).

    Provides a bordered frame around the plot with consistent sizing,
    state indicator, identity label, and animation support.
    """

    maximize_requested = pyqtSignal()
    park_requested = pyqtSignal()
    status_message_requested = pyqtSignal(str)
    color_changed = pyqtSignal(object, object)  # (ProbeAnchor, QColor)
    overlay_requested = pyqtSignal(object, object)  # (self/panel, ProbeAnchor)
    equation_overlay_requested = pyqtSignal(object, str)  # (self/panel, eq_id)
    overlay_remove_requested = pyqtSignal(object, object)  # (self/panel, overlay_anchor)

    def __init__(
        self,
        anchor: ProbeAnchor,
        color: QColor,
        dtype: str,
        trace_id: str = "",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._anchor = anchor
        self._color = color
        self._dtype = dtype
        self._trace_id = trace_id
        self._plot: Optional[BasePlot] = None
        self._current_plugin: Optional['ProbePlugin'] = None
        self._removal_animation = None
        self._layout: Optional[QVBoxLayout] = None
        self._lens_dropdown: Optional[LensDropdown] = None
        self._toolbar: Optional[PlotToolbar] = None
        self._focus_style_base = ""
        self._debug_overlay = None  # Ctrl+Shift+D layout debug overlay
        
        # Track interaction mode and saved ranges for axis-constrained zoom
        self._current_interaction_mode = InteractionMode.POINTER
        self._saved_x_range = None
        self._saved_y_range = None

        self._marker_vault = {}  # lens_name -> list[MarkerData]

        self._setup_ui()

        # M2.5: Focus policy for keyboard shortcuts
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        # M2.5: Accept drops for signal overlay
        self.setAcceptDrops(True)

        from .theme.theme_manager import ThemeManager
        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.current)

    def _setup_ui(self):
        """Create the panel UI."""
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)

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

        # Trace ID label (e.g., tr0)
        self._id_label = QLabel(self._trace_id)
        self._id_label.setStyleSheet("color: #00ffff; font-weight: bold; font-family: monospace; font-size: 11px;")
        header.addWidget(self._id_label)

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

        # Connect plot widget's hover coordinate signal if present
        if hasattr(self._plot, 'status_message_requested'):
            self._plot.status_message_requested.connect(self.status_message_requested)

        # Set minimum size
        self.setMinimumSize(300, 250)

        # M2.5: Toolbar overlay (positioned at top-right)
        self._toolbar = PlotToolbar(self)
        self._toolbar.mode_changed.connect(self._on_toolbar_mode_changed)
        self._toolbar.reset_requested.connect(self._on_toolbar_reset)
        
        # Apply initial POINTER mode to disable mouse pan/zoom by default
        self._on_toolbar_mode_changed(InteractionMode.POINTER)

        # Store base stylesheet for focus indicator toggling
        self._focus_style_base = self.styleSheet()

    def _apply_theme(self, theme) -> None:
        c = theme.colors
        base_style = f"""
            ProbePanel {{
                border: 1px solid {c['border_default']};
                border-radius: 6px;
                background-color: {c['bg_dark']};
            }}
            ProbePanel:hover {{
                border-color: {c['accent_primary']};
            }}
        """
        self.setStyleSheet(base_style)
        self._focus_style_base = base_style
        self._throttle_label.setStyleSheet(
            f"QLabel {{ color: {c['warning']}; font-size: 12px; }}"
        )

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
                # Emit signal for MainWindow to track lens preference - but block to prevent 
                # _on_lens_changed being called again (it's already connected to this signal)
                self._lens_dropdown.blockSignals(True)
                self._lens_dropdown.lens_changed.emit(current_lens_name)
                self._lens_dropdown.blockSignals(False)
                # _on_lens_changed already updated the new widget with self._data
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

    def update_from_buffer(self, buffer: ProbeDataBuffer) -> None:
        """Update the plot using the full capture buffer."""
        timestamps, values = buffer.get_plot_data()
        if not values:
            return

        dtype = buffer.last_dtype or self._dtype
        shape = buffer.last_shape

        # If dtype changed, we MUST call update_data to allow widget recreation
        # before trying to use update_history (which would bypass the dtype-change logic)
        if dtype != self._dtype:
            self.update_data(values[-1], dtype, shape)
            # After widget recreation, immediately replace with full buffer
            # to restore append-then-replace behavior
            if self._plot and hasattr(self._plot, "update_history"):
                self._plot.update_history(values)
            return

        # Prefer update_history for widgets that support it (like ScalarHistoryWidget)
        if hasattr(self._plot, "update_history"):
            self._plot.update_history(values)
        else:
            # Fallback to updating with just the latest value
            self.update_data(values[-1], dtype, shape)

    def _on_lens_changed(self, plugin_name: str):
        """Handle lens change - swap out the plot widget."""
        from ..plugins import PluginRegistry
        from PyQt6.QtCore import QTimer
        
        registry = PluginRegistry.instance()
        plugin = registry.get_plugin_by_name(plugin_name, getattr(self, '_dtype', None))
        
        if not plugin:
            return
            
        # Capture markers before disposing old widget
        if self._plot and hasattr(self._plot, '_marker_store'):
            old_lens = self._current_plugin.name if self._current_plugin else "Unknown"
            self._marker_vault[old_lens] = self._plot._marker_store.get_markers()
            # Dispose old marker store but KEEP the IDs in the global registry
            self._plot._marker_store.dispose(release_ids=False)

        # Remove old plot widget
        if self._plot:
            self._plot.hide()  # Hide immediately to prevent visual overlap
            self._layout.removeWidget(self._plot)
            self._plot.deleteLater()
        
        # Create new widget from plugin
        self._current_plugin = plugin
        self._plot = plugin.create_widget(self._anchor.symbol, self._color, self)
        
        # Restore markers from vault if any
        if hasattr(self._plot, '_marker_store'):
            parked = self._marker_vault.get(plugin_name, [])
            for m_data in parked:
                self._plot._marker_store.add_marker_data(m_data)

        # Insert into layout (index 1, after header)
        self._layout.insertWidget(1, self._plot)
        self._plot.show()  # Ensure new widget is visible

        # Connect plot widget's hover coordinate signal if present
        if hasattr(self._plot, 'status_message_requested'):
            self._plot.status_message_requested.connect(self.status_message_requested)
        
        # Re-apply current toolbar mode to new plot widget
        if self._toolbar:
            self._on_toolbar_mode_changed(self._toolbar.current_mode)
        
        # Re-apply data if we had any - but ONLY if widget doesn't support update_history.
        # For widgets with update_history (like ScalarHistoryWidget), update_from_buffer
        # will call update_history() which replaces the full buffer, making this redundant
        # and causing duplicate values.
        if hasattr(self, '_data') and self._data is not None:
            if not hasattr(self._plot, 'update_history'):
                # Capture current values in lambda closure
                data, dtype, shape = self._data, self._dtype, getattr(self, '_shape', None)
                QTimer.singleShot(0, lambda: plugin.update(self._plot, data, dtype, shape))

    @property
    def current_lens(self) -> str:
        """Get current lens name."""
        return self._lens_dropdown.currentText() if self._lens_dropdown else ""

    def contextMenuEvent(self, event):
        """Show context menu with View As... and Park options."""
        from .theme.theme_manager import ThemeManager
        c = ThemeManager.instance().current.colors
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {c['bg_medium']};
                color: {c['accent_primary']};
                border: 1px solid {c['accent_primary']};
            }}
            QMenu::item:selected {{
                background-color: {c['accent_primary']};
                color: {c['bg_medium']};
            }}
            QMenu::item:disabled {{
                color: {c['text_muted']};
            }}
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
        
        # Draw Mode submenu
        if self._plot and hasattr(self._plot, 'series_keys') and hasattr(self._plot, 'set_draw_mode'):
            from ..plots.draw_mode import DrawMode
            menu.addSeparator()
            
            keys = self._plot.series_keys
            if len(keys) == 1:
                # Single series: flat submenu
                draw_menu = menu.addMenu("Draw Mode")
                key = keys[0]
                current = self._plot.get_draw_mode(key)
                for mode in DrawMode:
                    label = mode.name.capitalize()
                    action = draw_menu.addAction(label)
                    action.setCheckable(True)
                    action.setChecked(current == mode)
                    action.triggered.connect(
                        lambda checked, k=key, m=mode: self._plot.set_draw_mode(k, m)
                    )
            elif len(keys) > 1:
                # Multi-series: nested per-series submenus
                draw_menu = menu.addMenu("Draw Mode")
                for key in keys:
                    series_menu = draw_menu.addMenu(str(key))
                    current = self._plot.get_draw_mode(key)
                    for mode in DrawMode:
                        label = mode.name.capitalize()
                        action = series_menu.addAction(label)
                        action.setCheckable(True)
                        action.setChecked(current == mode)
                        action.triggered.connect(
                            lambda checked, k=key, m=mode: self._plot.set_draw_mode(k, m)
                        )
        
        # M2.5: Park to bar action
        menu.addSeparator()
        park_action = menu.addAction("Park to Bar")
        park_action.triggered.connect(lambda: self.park_requested.emit())
        
        # Change Color action
        menu.addSeparator()
        has_series = (self._plot and hasattr(self._plot, 'series_keys')
                      and hasattr(self._plot, 'set_series_color'))
        if has_series and len(self._plot.series_keys) > 1:
            color_menu = menu.addMenu("Change Color…")
            keys = self._plot.series_keys
            for idx, key in enumerate(keys):
                action = color_menu.addAction(str(key))
                action.triggered.connect(
                    lambda checked, k=key, i=idx: self._change_series_color(k, i)
                )
        else:
            change_color_action = menu.addAction("Change Color…")
            change_color_action.triggered.connect(self._change_probe_color)
            
        # M4: Markers submenu
        if self._plot and hasattr(self._plot, '_marker_store'):
            menu.addSeparator()
            marker_menu = menu.addMenu("Markers")
            
            add_action = marker_menu.addAction("Add Marker at Center")
            add_action.triggered.connect(self._add_marker_at_center)
            
            marker_menu.addSeparator()
            
            manager_action = marker_menu.addAction("Marker Manager…")
            manager_action.triggered.connect(self._show_marker_manager)
            
            marker_menu.addSeparator()
            
            clear_action = marker_menu.addAction("Clear All Markers")
            clear_action.triggered.connect(self._clear_all_markers)
            
            from .theme.theme_manager import ThemeManager
            c = ThemeManager.instance().current.colors
            marker_menu.setStyleSheet(f"""
                QMenu {{
                    background-color: {c['bg_medium']};
                    color: {c['accent_primary']};
                    border: 1px solid {c['accent_primary']};
                }}
                QMenu::item:selected {{
                    background-color: {c['accent_primary']};
                    color: {c['bg_medium']};
                }}
            """)
        
        # M2.5: Remove Overlays submenu (if any overlays exist)
        if hasattr(self, '_overlay_anchors') and self._overlay_anchors:
            menu.addSeparator()
            overlay_menu = menu.addMenu("Remove Overlays")
            for overlay in self._overlay_anchors:
                action = overlay_menu.addAction(overlay.symbol)
                # Capture anchor in closure using default argument
                action.triggered.connect(
                    lambda checked, oa=overlay: self.overlay_remove_requested.emit(self, oa)
                )
        
        menu.exec(event.globalPos())

    def set_state(self, state: ProbeState):
        """Update the state indicator."""
        self._state_indicator.set_state(state)

    def _change_probe_color(self) -> None:
        """Open color dialog and update the probe's primary color."""
        new_color = QColorDialog.getColor(self._color, self, "Select Plot Color")
        if not new_color.isValid():
            return
        self._color = new_color
        hex_color = new_color.name()
        self._identity_label.setStyleSheet(f"""
            QLabel {{
                color: {hex_color};
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        if self._plot and hasattr(self._plot, 'set_color'):
            self._plot.set_color(new_color)
        self.color_changed.emit(self._anchor, new_color)

    def _change_series_color(self, series_key, series_index: int) -> None:
        """Open color dialog and update a specific series' color."""
        # Get current color from series if possible
        initial = self._color
        if self._plot and hasattr(self._plot, '_series_curves'):
            if series_key in self._plot._series_curves:
                _, hex_c = self._plot._series_curves[series_key]
                initial = QColor(hex_c)
        new_color = QColorDialog.getColor(initial, self, f"Select Color for {series_key}")
        if not new_color.isValid():
            return
        if self._plot and hasattr(self._plot, 'set_series_color'):
            self._plot.set_series_color(series_key, new_color)
        # If this is the first/primary series, also update panel identity and emit signal
        if series_index == 0:
            self._color = new_color
            hex_color = new_color.name()
            self._identity_label.setStyleSheet(f"""
                QLabel {{
                    color: {hex_color};
                    font-size: 11px;
                    font-weight: bold;
                }}
            """)
            self.color_changed.emit(self._anchor, new_color)

    def _add_marker_at_center(self):
        if not self._plot or not hasattr(self._plot, '_marker_store'):
            return
            
        store = self._plot._marker_store
        
        # Determine trace key
        trace_key = 0
        if hasattr(self._plot, 'series_keys') and len(self._plot.series_keys) > 0:
            trace_key = self._plot.series_keys[0]
        elif hasattr(self._plot, '_curves') and len(self._plot._curves) > 0:
            trace_key = 0
            
        # Get center
        x_center = 0.0
        y_center = 0.0
        if hasattr(self._plot, '_plot_widget'):
            vb = self._plot._plot_widget.getPlotItem().getViewBox()
            xr, yr = vb.viewRange()
            x_center = sum(xr) / 2
            y_center = sum(yr) / 2
            
        store.add_marker(trace_key, x_center, y_center)
        
    def _show_marker_manager(self):
        if not self._plot or not hasattr(self._plot, '_marker_store'):
            return
        from .marker_manager import MarkerManager
        MarkerManager.show_instance(self.window())

    def _clear_all_markers(self):
        if self._plot and hasattr(self._plot, '_marker_store'):
            self._plot._marker_store.clear_markers()

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

    # === M2.5: Hover toolbar show/hide ===

    def enterEvent(self, event) -> None:
        """Show toolbar on mouse enter."""
        super().enterEvent(event)
        if self._toolbar:
            self._toolbar.show_on_hover()

    def leaveEvent(self, event) -> None:
        """Hide toolbar on mouse leave."""
        super().leaveEvent(event)
        if self._toolbar:
            self._toolbar.hide_on_leave()

    def resizeEvent(self, event) -> None:
        """Reposition toolbar on resize."""
        super().resizeEvent(event)
        if self._toolbar:
            # Position at bottom-right of panel
            self._toolbar.move(
                self.width() - self._toolbar.sizeHint().width() - 8,
                self.height() - self._toolbar.sizeHint().height() - 8
            )
            self._toolbar.raise_()  # Ensure topmost z-order
            
            # Pass toolbar geometry to pin indicator for dynamic positioning
            if self._plot and hasattr(self._plot, '_pin_indicator') and self._plot._pin_indicator:
                self._plot._pin_indicator.set_toolbar_rect(self._toolbar.geometry())

    # === M2.5: Toolbar mode handling ===

    def _on_toolbar_mode_changed(self, mode: InteractionMode) -> None:
        """Handle interaction mode change from toolbar."""
        self._current_interaction_mode = mode
        logger.debug(f"Toolbar mode changed to {mode.name}")
        
        if self._plot and hasattr(self._plot, '_plot_widget'):
            vb = self._plot._plot_widget.getPlotItem().getViewBox()
            
            # Restore original setRange if we had patched it
            if hasattr(vb, '_original_setRange'):
                vb.setRange = vb._original_setRange
                del vb._original_setRange
                logger.debug("  Restored original setRange")
            
            # Get current ranges for constraining
            x_range, y_range = vb.viewRange()
            self._saved_x_range = list(x_range)
            self._saved_y_range = list(y_range)
            
            if mode == InteractionMode.PAN:
                vb.setMouseEnabled(x=True, y=True)
                vb.setMouseMode(vb.PanMode)
            elif mode == InteractionMode.ZOOM:
                vb.setMouseEnabled(x=True, y=True)
                vb.setMouseMode(vb.RectMode)
            elif mode == InteractionMode.ZOOM_X:
                # X-only zoom: patch setRange to ignore Y changes
                vb.setMouseEnabled(x=True, y=True)
                vb.setMouseMode(vb.RectMode)
                self._plot._plot_widget.setAspectLocked(False)
                self._patch_setrange_for_axis(vb, 'x')
                logger.debug(f"  ZOOM_X: Patched setRange to lock Y at {self._saved_y_range}")
            elif mode == InteractionMode.ZOOM_Y:
                # Y-only zoom: patch setRange to ignore X changes
                vb.setMouseEnabled(x=True, y=True)
                vb.setMouseMode(vb.RectMode)
                self._plot._plot_widget.setAspectLocked(False)
                self._patch_setrange_for_axis(vb, 'y')
                logger.debug(f"  ZOOM_Y: Patched setRange to lock X at {self._saved_x_range}")
            else:
                # POINTER mode: disable mouse pan/zoom entirely
                vb.setMouseMode(vb.PanMode)
                vb.setMouseEnabled(x=False, y=False)
    
    def _patch_setrange_for_axis(self, vb, allowed_axis: str):
        """Monkey-patch ViewBox.setRange to constrain zoom to one axis."""
        import types
        from PyQt6.QtCore import QRectF
        
        # Store original method
        vb._original_setRange = vb.setRange
        saved_x = self._saved_x_range
        saved_y = self._saved_y_range
        
        def constrained_setRange(rect=None, xRange=None, yRange=None, padding=None,
                                  update=True, disableAutoRange=True):
            # If rect is provided (from RectMode zoom), extract and constrain
            if rect is not None:
                if isinstance(rect, QRectF):
                    if allowed_axis == 'x':
                        # Keep Y fixed, only apply X from rect
                        xRange = [rect.left(), rect.right()]
                        yRange = saved_y
                        rect = None
                    else:  # allowed_axis == 'y'
                        # Keep X fixed, only apply Y from rect
                        xRange = saved_x
                        yRange = [rect.top(), rect.bottom()]
                        rect = None
            else:
                # For explicit xRange/yRange calls, constrain appropriately
                if allowed_axis == 'x' and yRange is not None:
                    yRange = saved_y
                elif allowed_axis == 'y' and xRange is not None:
                    xRange = saved_x
            
            # Update saved range for the moving axis
            if allowed_axis == 'x' and xRange is not None:
                saved_x[0], saved_x[1] = xRange[0], xRange[1]
            elif allowed_axis == 'y' and yRange is not None:
                saved_y[0], saved_y[1] = yRange[0], yRange[1]
            
            return vb._original_setRange(rect=rect, xRange=xRange, yRange=yRange,
                                          padding=padding, update=update,
                                          disableAutoRange=disableAutoRange)
        
        vb.setRange = types.MethodType(lambda self, *args, **kwargs: constrained_setRange(*args, **kwargs), vb)

    def _on_toolbar_reset(self) -> None:
        """Handle reset from toolbar."""
        # Restore original setRange if axis-constrained zoom had patched it
        if self._plot and hasattr(self._plot, '_plot_widget'):
            vb = self._plot._plot_widget.getPlotItem().getViewBox()
            if hasattr(vb, '_original_setRange'):
                vb.setRange = vb._original_setRange
                del vb._original_setRange
        # Reset toolbar mode to POINTER (clears zoom constraints)
        if self._toolbar:
            self._toolbar.set_mode(InteractionMode.POINTER)
        # Prefer reset_view() which restores full curve data before auto-ranging
        if self._plot and hasattr(self._plot, 'reset_view'):
            self._plot.reset_view()
        elif self._plot and hasattr(self._plot, 'axis_controller'):
            ac = self._plot.axis_controller
            if ac:
                ac.reset()

    # === M2.5: Drag-and-drop overlay ===

    def dragEnterEvent(self, event) -> None:
        """Accept anchor or equation drags for signal overlay."""
        mime = event.mimeData()
        if mime and (has_anchor_mime(mime) or mime.hasFormat("application/x-pyprobe-equation")):
            event.acceptProposedAction()
            self._show_drop_highlight(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        """Remove drop highlight on drag leave."""
        self._show_drop_highlight(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        """Handle drop of anchor or equation data for overlay."""
        self._show_drop_highlight(False)
        mime = event.mimeData()
        if not mime:
            return

        if has_anchor_mime(mime):
            data = decode_anchor_mime(mime)
            if data:
                anchor = ProbeAnchor(
                    file=data['file'],
                    line=data['line'],
                    col=data['col'],
                    symbol=data['symbol'],
                    func=data.get('func', ''),
                    is_assignment=data.get('is_assignment', False),
                )
                self.overlay_requested.emit(self, anchor)
                event.acceptProposedAction()
        elif mime.hasFormat("application/x-pyprobe-equation"):
            eq_id = mime.data("application/x-pyprobe-equation").data().decode()
            self.equation_overlay_requested.emit(self, eq_id)
            event.acceptProposedAction()
        else:
            event.ignore()

    def _show_drop_highlight(self, show: bool) -> None:
        """Show or hide green drop target highlight."""
        if show:
            from .theme.theme_manager import ThemeManager
            c = ThemeManager.instance().current.colors
            self.setStyleSheet(f"""
                ProbePanel {{
                    border: 2px solid {c['success']};
                    border-radius: 6px;
                    background-color: {c['bg_dark']};
                }}
            """)
        else:
            self.setStyleSheet(self._focus_style_base)

    # === M2.5: Focus indicator + keyboard shortcuts ===

    def focusInEvent(self, event) -> None:
        """Show focus glow when panel gains keyboard focus."""
        self._show_focus_indicator(True)
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        """Remove focus glow when panel loses keyboard focus."""
        self._show_focus_indicator(False)
        super().focusOutEvent(event)

    def _show_focus_indicator(self, focused: bool) -> None:
        """Toggle cyan border glow for focused state."""
        if focused:
            from .theme.theme_manager import ThemeManager
            c = ThemeManager.instance().current.colors
            self.setStyleSheet(f"""
                ProbePanel {{
                    border: 1px solid {c['accent_primary']};
                    border-radius: 6px;
                    background-color: {c['bg_dark']};
                }}
            """)
        else:
            self.setStyleSheet(self._focus_style_base)

    def keyPressEvent(self, event) -> None:
        """Handle keyboard shortcuts for focused panel."""
        key = event.key()
        logger.debug(f"ProbePanel.keyPressEvent: key={key}, Qt.Key.Key_X={Qt.Key.Key_X}, Qt.Key.Key_Y={Qt.Key.Key_Y}")
        if key == Qt.Key.Key_X:
            logger.debug("  X key pressed, toggling X axis pin")
            if self._plot and hasattr(self._plot, 'axis_controller') and self._plot.axis_controller:
                self._plot.axis_controller.toggle_pin('x')
            else:
                logger.debug("  No axis_controller found!")
        elif key == Qt.Key.Key_Y:
            logger.debug("  Y key pressed, toggling Y axis pin")
            if self._plot and hasattr(self._plot, 'axis_controller') and self._plot.axis_controller:
                self._plot.axis_controller.toggle_pin('y')
            else:
                logger.debug("  No axis_controller found!")
        elif key == Qt.Key.Key_R:
            # Delegate to _on_toolbar_reset which handles setRange restore
            self._on_toolbar_reset()
        elif key == Qt.Key.Key_M:
            # M for Maximize toggle
            self.maximize_requested.emit()
        elif key == Qt.Key.Key_Escape:
            if self._toolbar:
                self._toolbar.set_mode(InteractionMode.POINTER)
        elif key == Qt.Key.Key_D and event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
            self._toggle_debug_overlay()
        elif key == Qt.Key.Key_P:
            # P for Park
            self.park_requested.emit()
        else:
            super().keyPressEvent(event)

    # === Phase 4: Debug overlay ===

    def _toggle_debug_overlay(self) -> None:
        """Toggle the Ctrl+Shift+D layout debug overlay."""
        from .debug_overlay import DebugOverlay

        if self._debug_overlay is None:
            self._debug_overlay = DebugOverlay(self)

        if self._debug_overlay.isVisible():
            self._debug_overlay.hide()
        else:
            self._refresh_debug_overlay()
            self._debug_overlay.show()

    def _refresh_debug_overlay(self) -> None:
        """Collect bounding boxes and push them to the debug overlay."""
        if self._debug_overlay is None:
            return

        self._debug_overlay.setGeometry(0, 0, self.width(), self.height())

        regions: dict = {}

        # Toolbar
        if self._toolbar:
            regions['toolbar'] = self._toolbar.geometry()

        # Plot area (ViewBox)
        if self._plot and hasattr(self._plot, '_plot_widget'):
            pw = self._plot._plot_widget
            vb = pw.getPlotItem().getViewBox()
            from pyprobe.plots.pin_layout_mixin import PinLayoutMixin
            regions['plot_area'] = PinLayoutMixin._get_mapped_rect(pw, self, vb)

        # Pin buttons
        if self._plot and hasattr(self._plot, '_pin_indicator') and self._plot._pin_indicator:
            pi = self._plot._pin_indicator
            # Map pin button positions from pin indicator to self
            x_geo = pi._x_btn.geometry()
            y_geo = pi._y_btn.geometry()
            x_tl = pi.mapTo(self, x_geo.topLeft())
            y_tl = pi.mapTo(self, y_geo.topLeft())
            from PyQt6.QtCore import QRectF
            regions['x_pin'] = QRectF(float(x_tl.x()), float(x_tl.y()), x_geo.width(), x_geo.height())
            regions['y_pin'] = QRectF(float(y_tl.x()), float(y_tl.y()), y_geo.width(), y_geo.height())

        self._debug_overlay.set_regions(regions)
        self._debug_overlay.raise_()

    @property
    def anchor(self) -> ProbeAnchor:
        """Return the probe anchor."""
        return self._anchor

    @property
    def var_name(self) -> str:
        """Return variable name (for backwards compatibility)."""
        return self._anchor.symbol

    def get_plot_data(self) -> dict:
        """
        Return the data currently plotted on the graph.
        
        Delegates to the underlying plot widget's get_plot_data() method
        which uses pyqtgraph's curve.getData() API.
        
        Returns:
            dict with 'x' and 'y' keys containing lists of values,
            or empty dict if no data available.
        """
        if self._plot and hasattr(self._plot, 'get_plot_data'):
            return self._plot.get_plot_data()
        return {'x': [], 'y': []}

    def get_marker_state(self) -> dict:
        """Return a dictionary mapping lens names to lists of MarkerData."""
        from ..plots.marker_model import MarkerData
        state = {lens: list(markers) for lens, markers in self._marker_vault.items()}
        
        # Add active markers
        if self._plot and hasattr(self._plot, '_marker_store'):
            active_lens = self._current_plugin.name if self._current_plugin else "Unknown"
            state[active_lens] = self._plot._marker_store.get_markers()
            
        return state

    def restore_marker_state(self, state: dict):
        """Restore marker state from a dictionary of MarkerSpec objects."""
        from ..plots.marker_model import MarkerData, MarkerType, MarkerShape
        
        self._marker_vault = {}
        for lens_name, spec_list in state.items():
            markers = []
            for spec in spec_list:
                m = MarkerData(
                    id=spec.id,
                    x=spec.x,
                    y=spec.y,
                    trace_key=spec.trace_key,
                    marker_type=MarkerType[spec.marker_type],
                    ref_marker_id=spec.ref_marker_id,
                    label=spec.label,
                    shape=MarkerShape[spec.shape] if spec.shape else None,
                    color=spec.color or '#ffffff'
                )
                markers.append(m)
            self._marker_vault[lens_name] = markers
            
        # If any markers for current lens, inject them
        if self._plot and hasattr(self._plot, '_marker_store'):
            active_lens = self._current_plugin.name if self._current_plugin else "Unknown"
            parked = self._marker_vault.get(active_lens, [])
            if parked:
                self._plot._marker_store.clear_markers()
                for m_data in parked:
                    self._plot._marker_store.add_marker_data(m_data)

