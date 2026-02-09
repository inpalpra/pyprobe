"""
Container widget for probe panels with flow layout.
"""

from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel, QMenu
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


class ProbePanel(QFrame):
    """
    Container for a single probe (plot widget).

    Provides a bordered frame around the plot with consistent sizing,
    state indicator, identity label, and animation support.
    """

    # M2.5: Signals
    maximize_requested = pyqtSignal()
    park_requested = pyqtSignal()
    overlay_requested = pyqtSignal(object, object)  # (self/panel, ProbeAnchor)
    overlay_remove_requested = pyqtSignal(object, object)  # (self/panel, overlay_anchor)

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
        self._toolbar: Optional[PlotToolbar] = None
        self._focus_style_base = ""
        
        # Track interaction mode and saved ranges for axis-constrained zoom
        self._current_interaction_mode = InteractionMode.POINTER
        self._saved_x_range = None
        self._saved_y_range = None

        self._setup_ui()

        # M2.5: Focus policy for keyboard shortcuts
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        # M2.5: Accept drops for signal overlay
        self.setAcceptDrops(True)

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

        # M2.5: Toolbar overlay (positioned at top-right)
        self._toolbar = PlotToolbar(self)
        self._toolbar.mode_changed.connect(self._on_toolbar_mode_changed)
        self._toolbar.reset_requested.connect(self._on_toolbar_reset)
        
        # Apply initial POINTER mode to disable mouse pan/zoom by default
        self._on_toolbar_mode_changed(InteractionMode.POINTER)

        # Store base stylesheet for focus indicator toggling
        self._focus_style_base = self.styleSheet()

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

    def _on_lens_changed(self, plugin_name: str):
        """Handle lens change - swap out the plot widget."""
        from ..plugins import PluginRegistry
        from PyQt6.QtCore import QTimer
        
        registry = PluginRegistry.instance()
        plugin = registry.get_plugin_by_name(plugin_name)
        
        if not plugin:
            return
        
        # Remove old plot widget
        if self._plot:
            self._plot.hide()  # Hide immediately to prevent visual overlap
            self._layout.removeWidget(self._plot)
            self._plot.deleteLater()
        
        # Create new widget from plugin
        self._current_plugin = plugin
        self._plot = plugin.create_widget(self._anchor.symbol, self._color, self)
        
        # Insert into layout (index 1, after header)
        self._layout.insertWidget(1, self._plot)
        self._plot.show()  # Ensure new widget is visible
        
        # Re-apply current toolbar mode to new plot widget
        if self._toolbar:
            self._on_toolbar_mode_changed(self._toolbar.current_mode)
        
        # Re-apply data if we had any - defer with QTimer to ensure widget is realized
        if hasattr(self, '_data') and self._data is not None:
            # Capture current values in lambda closure
            data, dtype, shape = self._data, self._dtype, getattr(self, '_shape', None)
            QTimer.singleShot(0, lambda: plugin.update(self._plot, data, dtype, shape))

    @property
    def current_lens(self) -> str:
        """Get current lens name."""
        return self._lens_dropdown.currentText() if self._lens_dropdown else ""

    def contextMenuEvent(self, event):
        """Show context menu with View As... and Park options."""
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
        
        # M2.5: Park to bar action
        menu.addSeparator()
        park_action = menu.addAction("Park to Bar")
        park_action.triggered.connect(lambda: self.park_requested.emit())
        
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
        if self._plot and hasattr(self._plot, 'axis_controller'):
            ac = self._plot.axis_controller
            if ac:
                ac.reset()

    # === M2.5: Double-click maximize ===

    def mouseDoubleClickEvent(self, event) -> None:
        """Toggle maximize on double-click of plot background."""
        # Only trigger on empty background, not axis/trace areas
        self.maximize_requested.emit()
        event.accept()

    # === M2.5: Drag-and-drop overlay ===

    def dragEnterEvent(self, event) -> None:
        """Accept anchor drags for signal overlay."""
        if event.mimeData() and has_anchor_mime(event.mimeData()):
            event.acceptProposedAction()
            self._show_drop_highlight(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        """Remove drop highlight on drag leave."""
        self._show_drop_highlight(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        """Handle drop of anchor data for overlay."""
        self._show_drop_highlight(False)
        if event.mimeData() and has_anchor_mime(event.mimeData()):
            data = decode_anchor_mime(event.mimeData())
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
            else:
                event.ignore()
        else:
            event.ignore()

    def _show_drop_highlight(self, show: bool) -> None:
        """Show or hide green drop target highlight."""
        if show:
            self.setStyleSheet("""
                ProbePanel {
                    border: 2px solid #00ff7f;
                    border-radius: 6px;
                    background-color: #0d0d0d;
                }
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
            self.setStyleSheet("""
                ProbePanel {
                    border: 1px solid #00ffff;
                    border-radius: 6px;
                    background-color: #0d0d0d;
                }
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
            if self._plot and hasattr(self._plot, 'axis_controller') and self._plot.axis_controller:
                self._plot.axis_controller.reset()
        elif key == Qt.Key.Key_Escape:
            if self._toolbar:
                self._toolbar.set_mode(InteractionMode.POINTER)
        else:
            super().keyPressEvent(event)

    @property
    def anchor(self) -> ProbeAnchor:
        """Return the probe anchor."""
        return self._anchor

    @property
    def var_name(self) -> str:
        """Return variable name (for backwards compatibility)."""
        return self._anchor.symbol

