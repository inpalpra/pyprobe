"""
Probe lifecycle controller.

Extracted from MainWindow to separate concerns.
Handles: probe add/remove, lens preferences, overlay registration and rendering.
"""

from typing import Dict, Optional, List, Callable
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget
import sip

from pyprobe.logging import get_logger
logger = get_logger(__name__)

from ..core.anchor import ProbeAnchor
from ..ipc.messages import make_add_probe_cmd, make_remove_probe_cmd
from .probe_panel import ProbePanel, RemovableLegendItem


def is_obj_deleted(obj):
    """Safely check if a Qt object has been deleted."""
    return obj is None or sip.isdeleted(obj)


class ProbeController(QObject):
    """
    Manages probe lifecycle and overlay coordination.
    
    Responsibilities:
    - Probe add/remove with UI updates
    - Lens preference tracking
    - Overlay registration and data forwarding
    - Overlay rendering to waveform/constellation plots
    
    Signals:
        probe_added: Emitted when probe is added (anchor, panel)
        probe_removed: Emitted when probe is removed (anchor)
        status_message: Status bar message (message)
    """
    
    probe_added = pyqtSignal(object, object)  # anchor, panel
    probe_removed = pyqtSignal(object)  # anchor
    status_message = pyqtSignal(str)
    
    # Overlay signals (forwarded from panels)
    overlay_requested = pyqtSignal(object, object)  # (target_panel, overlay_anchor)
    equation_overlay_requested = pyqtSignal(object, str)  # (target_panel, eq_id)
    overlay_remove_requested = pyqtSignal(object, object)  # (target_panel, overlay_anchor)
    
    def __init__(
        self, 
        registry,
        container,
        code_viewer,
        gutter,
        get_ipc: Callable,
        get_is_running: Callable,
        parent: Optional[QObject] = None
    ):
        """
        Initialize ProbeController.
        
        Args:
            registry: ProbeRegistry for probe state management
            container: ProbePanelContainer for creating panels
            code_viewer: CodeViewer for highlight updates
            gutter: CodeGutter for gutter markers
            get_ipc: Callable returning current IPC channel (or None)
            get_is_running: Callable returning whether script is running
            parent: Parent QObject
        """
        super().__init__(parent)
        self._registry = registry
        self._container = container
        self._code_viewer = code_viewer
        self._gutter = gutter
        self._get_ipc = get_ipc
        self._get_is_running = get_is_running
        
        # Probe panels by anchor - supports multiple panels per anchor via Ctrl+click
        self._probe_panels: Dict[ProbeAnchor, List[QWidget]] = {}
        
        # Probe metadata (lens preferences, dtype, overlay target)
        self._probe_metadata: Dict[ProbeAnchor, dict] = {}
        
        # Pending overlay data: buffered when panel._plot is None
        # Key: id(panel), Value: list of (overlay_key, payload) tuples
        self._pending_overlays: Dict[int, list] = {}
    
    @property
    def probe_panels(self) -> Dict[ProbeAnchor, List[QWidget]]:
        """Access to probe panels dict."""
        return self._probe_panels
    
    @property
    def probe_metadata(self) -> Dict[ProbeAnchor, dict]:
        """Access to probe metadata dict."""
        return self._probe_metadata
    
    def add_probe(self, anchor: ProbeAnchor, lens_name: Optional[str] = None) -> Optional[QWidget]:
        """
        Add a probe for the given anchor.
        
        Args:
            anchor: The anchor to probe
            lens_name: Optional lens preference to apply immediately
            
        Returns:
            The created ProbePanel, or None if registry is full
        """
        logger.debug(f"add_probe called with anchor: {anchor}, lens: {lens_name}")
        
        if self._registry.is_full():
            logger.debug("Registry is full, returning")
            self.status_message.emit("Maximum probes reached (100)")
            return None
        
        # Add to registry and get assigned color
        color = self._registry.add_probe(anchor)
        logger.debug(f"Probe added, assigned color: {color.name() if color else 'None'}")
        
        # Initialize metadata
        if anchor not in self._probe_metadata:
            self._probe_metadata[anchor] = {
                'lens': lens_name,
                'dtype': None
            }
        elif lens_name:
            self._probe_metadata[anchor]['lens'] = lens_name

        # Check if this is the first panel for this anchor
        is_first_panel = anchor not in self._probe_panels or not self._probe_panels[anchor]

        # Only update code viewer highlight for FIRST panel (not duplicates)
        # This ensures ref_count matches: 1 for graphical probes, incremented separately for watch
        if is_first_panel:
            self._code_viewer.set_probe_active(anchor, color)
            self._gutter.set_probed_line(anchor.line, color)

        # Get Trace ID
        trace_id = self._registry.get_trace_id(anchor) or ""

        # Create probe panel
        panel = self._container.create_probe_panel(anchor, color, trace_id)
        if anchor not in self._probe_panels:
            self._probe_panels[anchor] = []
        self._probe_panels[anchor].append(panel)
        
        # Connect hover coordinate signal
        panel.status_message_requested.connect(self.status_message.emit)
        
        # Connect overlay signals
        panel.overlay_requested.connect(self.overlay_requested.emit)
        panel.equation_overlay_requested.connect(self.equation_overlay_requested.emit)
        panel.overlay_remove_requested.connect(self.overlay_remove_requested.emit)
        
        # Connect lens changed signal
        if hasattr(panel, '_lens_dropdown') and panel._lens_dropdown:
            from functools import partial
            panel._lens_dropdown.lens_changed.connect(
                partial(self.handle_lens_changed, anchor)
            )
            
            # If we have a stored lens preference, apply it
            stored_lens = self._probe_metadata[anchor].get('lens')
            if stored_lens:
                panel._lens_dropdown.set_lens(stored_lens)
        
        # Connect color changed signal
        panel.color_changed.connect(self._on_probe_color_changed)
        
        # Send to runner if running
        ipc = self._get_ipc()
        if ipc and self._get_is_running():
            msg = make_add_probe_cmd(anchor)
            ipc.send_command(msg)
        
        self.status_message.emit(f"Probe added: {anchor.identity_label()}")
        self.probe_added.emit(anchor, panel)
        
        return panel
    
    def _on_probe_color_changed(self, anchor: ProbeAnchor, color: QColor) -> None:
        """Handle color change from a probe panel — update code viewer and gutter."""
        self._code_viewer.update_probe_color(anchor, color)
        self._gutter.set_probed_line(anchor.line, color)
    
    def remove_probe(self, anchor: ProbeAnchor, on_animation_done: Callable = None):
        """
        Start probe removal (with animation).

        Removes the most recently created panel for this anchor.

        Args:
            anchor: Anchor to remove
            on_animation_done: Callback after animation completes
        """
        logger.debug(f"remove_probe called with anchor: {anchor}")

        if anchor not in self._probe_panels or not self._probe_panels[anchor]:
            logger.debug("Anchor not in _probe_panels or no panels, returning early")
            return

        # Get the last panel (most recently created)
        panel = self._probe_panels[anchor][-1]

        # Import here to avoid circular import
        from .animations import ProbeAnimations

        # Animate removal, then complete
        if on_animation_done:
            ProbeAnimations.fade_out(panel, on_finished=on_animation_done)
        else:
            ProbeAnimations.fade_out(
                panel,
                on_finished=lambda p=panel: self.complete_probe_removal(anchor, p)
            )
    
    def complete_probe_removal(self, anchor: ProbeAnchor, panel=None):
        """Complete probe removal after animation.

        Args:
            anchor: The probe anchor
            panel: The specific panel to remove (if None, removes last panel)
        """
        logger.debug(f"complete_probe_removal called with anchor: {anchor}, panel: {panel}")

        # Remove specific panel from our list
        if anchor in self._probe_panels:
            panel_list = self._probe_panels[anchor]
            if panel is not None and panel in panel_list:
                panel_list.remove(panel)
                logger.debug(f"Removed specific panel, {len(panel_list)} remaining")
            elif panel_list:
                panel = panel_list.pop()
                logger.debug(f"Removed last panel, {len(panel_list)} remaining")

            # Clean up container
            self._container.remove_probe_panel(panel=panel)

            # Check if this was the last panel for this anchor
            if not panel_list:
                del self._probe_panels[anchor]
                logger.debug("No more panels for this anchor, cleaning up")

                # Remove from registry
                self._registry.remove_probe(anchor)
                logger.debug("Removed from registry")

                # Update code viewer
                self._code_viewer.remove_probe(anchor)

                # Update gutter
                self._gutter.clear_probed_line(anchor.line)

                # Send to runner if running
                ipc = self._get_ipc()
                if ipc and self._get_is_running():
                    msg = make_remove_probe_cmd(anchor)
                    ipc.send_command(msg)

        self.status_message.emit(f"Probe removed: {anchor.identity_label()}")
        self.probe_removed.emit(anchor)

        # Global cleanup of any deleted objects from _probe_panels to prevent RuntimeErrors
        for a in list(self._probe_panels.keys()):
            self._probe_panels[a] = [p for p in self._probe_panels[a] if not is_obj_deleted(p)]
            if not self._probe_panels[a]:
                del self._probe_panels[a]
    
    def handle_lens_changed(self, anchor: ProbeAnchor, lens_name: str):
        """Handle lens change from probe panel."""
        if anchor in self._probe_metadata:
            self._probe_metadata[anchor]['lens'] = lens_name
            logger.debug(f"Lens preference saved for {anchor.identity_label()}: {lens_name}")
    
    def handle_overlay_requested(self, target_panel, overlay_anchor: ProbeAnchor):
        """
        Handle overlay drop request - register overlay signal on target panel.
        
        Args:
            target_panel: The panel to add the overlay to
            overlay_anchor: The anchor to overlay
        """
        logger.debug(f"Overlay requested: {overlay_anchor.symbol} -> {target_panel._anchor.symbol}")
        
        # Check if this symbol is already probed (possibly with different anchor identity)
        # If so, use the existing anchor to ensure data forwarding matches correctly
        existing_anchor = None
        for anchor in self._registry.active_anchors:
            if anchor.symbol == overlay_anchor.symbol and anchor.line == overlay_anchor.line:
                existing_anchor = anchor
                break
        
        if existing_anchor is not None:
            # Use the existing anchor identity for overlay registration
            logger.debug(f"Using existing anchor for {overlay_anchor.symbol}")
            overlay_anchor = existing_anchor
        else:
            # Add to registry without creating a separate panel
            color = self._registry.add_probe(overlay_anchor)
            if color is None:
                self.status_message.emit("Maximum probes reached")
                return
            
            # Update code viewer to show it's probed
            self._code_viewer.set_probe_active(overlay_anchor, color)
            self._gutter.set_probed_line(overlay_anchor.line, color)
            
            # Initialize metadata
            self._probe_metadata[overlay_anchor] = {
                'lens': None,
                'dtype': None,
                'overlay_target': target_panel._anchor  # Track that this is an overlay
            }
            
            # Send probe command to runner
            ipc = self._get_ipc()
            if ipc and self._get_is_running():
                msg = make_add_probe_cmd(overlay_anchor)
                ipc.send_command(msg)
        
        # Register this overlay relationship for data forwarding
        if not hasattr(target_panel, '_overlay_anchors'):
            target_panel._overlay_anchors = []
        
        if overlay_anchor not in target_panel._overlay_anchors:
            target_panel._overlay_anchors.append(overlay_anchor)
            logger.debug(f"Added overlay anchor: {overlay_anchor.symbol} to panel {target_panel._anchor.symbol}")
        
        self.status_message.emit(f"Overlaid: {overlay_anchor.symbol} on {target_panel._anchor.symbol}")
    
    def remove_overlay(self, target_panel, overlay_anchor: ProbeAnchor):
        """
        Remove an overlay signal from a target panel.
        
        Args:
            target_panel: The panel to remove the overlay from
            overlay_anchor: The anchor to remove
        """
        logger.debug(f"Removing overlay: {overlay_anchor.symbol} from {target_panel._anchor.symbol}")
        
        # Remove from overlay anchors list
        if hasattr(target_panel, '_overlay_anchors'):
            if overlay_anchor in target_panel._overlay_anchors:
                target_panel._overlay_anchors.remove(overlay_anchor)
                logger.debug(f"Removed overlay anchor from list")
        
        # Remove curves from plot
        plot = target_panel._plot
        if plot is not None:
            # Build the overlay key used when adding curves
            overlay_key = f"{overlay_anchor.symbol}_{'lhs' if overlay_anchor.is_assignment else 'rhs'}"
            
            from pyprobe.plugins.builtins.waveform import WaveformWidget
            from pyprobe.plugins.builtins.constellation import ConstellationWidget
            
            if isinstance(plot, WaveformWidget):
                self._remove_overlay_from_waveform(plot, overlay_anchor)
            elif isinstance(plot, ConstellationWidget):
                self._remove_overlay_from_constellation(plot, overlay_anchor)
        
        # Check if this overlay anchor is used by any other panels
        anchor_still_used = False
        for panel_list in self._probe_panels.values():
            for panel in panel_list:
                if is_obj_deleted(panel):
                    continue
                if hasattr(panel, '_overlay_anchors') and overlay_anchor in panel._overlay_anchors:
                    anchor_still_used = True
                    break
            if anchor_still_used:
                break

        # If not used anywhere else and not a standalone probe, remove from registry
        if not anchor_still_used and overlay_anchor not in self._probe_panels:
            meta = self._probe_metadata.get(overlay_anchor)
            if meta and meta.get('overlay_target'):
                # This was an overlay-only anchor, clean up
                self._registry.remove_probe(overlay_anchor)
                self._code_viewer.remove_probe(overlay_anchor)
                self._gutter.clear_probed_line(overlay_anchor.line)
                if overlay_anchor in self._probe_metadata:
                    del self._probe_metadata[overlay_anchor]
                
                # Tell runner to stop tracking this probe
                ipc = self._get_ipc()
                if ipc and self._get_is_running():
                    msg = make_remove_probe_cmd(overlay_anchor)
                    ipc.send_command(msg)
        
        self.status_message.emit(f"Overlay removed: {overlay_anchor.symbol}")
    
    def _remove_overlay_from_waveform(self, plot, anchor: ProbeAnchor):
        """Remove overlay curves from a waveform plot."""
        if not hasattr(plot, "_overlay_curves_by_anchor"):
            return

        if anchor in plot._overlay_curves_by_anchor:
            curves = plot._overlay_curves_by_anchor.pop(anchor)
            for curve in curves:
                # Remove from plot widget
                plot._plot_widget.removeItem(curve)
                # Remove from legend if present
                if hasattr(plot, "_legend") and plot._legend is not None:
                    try:
                        plot._legend.removeItem(curve)
                    except Exception:
                        pass
                
                # Also remove from _overlay_curves dict (requires finding the key)
                keys_to_remove = [k for k, v in getattr(plot, "_overlay_curves", {}).items() if v is curve]
                for k in keys_to_remove:
                    del plot._overlay_curves[k]
                    
            logger.debug(f"Removed overlay curves for: {anchor.symbol}")
    
    def _remove_overlay_from_constellation(self, plot, anchor: ProbeAnchor):
        """Remove overlay scatter from a constellation plot."""
        if not hasattr(plot, "_overlay_scatters_by_anchor"):
            return

        if anchor in plot._overlay_scatters_by_anchor:
            scatters = plot._overlay_scatters_by_anchor.pop(anchor)
            for scatter in scatters:
                plot._plot_widget.removeItem(scatter)
                # Remove from legend if present
                if hasattr(plot, "_legend") and plot._legend is not None:
                    try:
                        plot._legend.removeItem(scatter)
                    except Exception:
                        pass
                
                # Also remove from _overlay_scatters dict
                keys_to_remove = [k for k, v in getattr(plot, "_overlay_scatters", {}).items() if v is scatter]
                for k in keys_to_remove:
                    del plot._overlay_scatters[k]
                    
            logger.debug(f"Removed overlay scatters for: {anchor.symbol}")
    
    def forward_overlay_data(self, anchor: ProbeAnchor, payload: dict):
        """
        Forward overlay probe data to target panels that have this anchor as overlay.

        When an overlay anchor's data arrives, we need to update the target panel's
        plot to show this data as an additional trace.
        """
        # Find all panels that have this anchor as an overlay
        for panel_list in self._probe_panels.values():
            for panel in panel_list:
                if is_obj_deleted(panel):
                    continue
                if not hasattr(panel, '_overlay_anchors'):
                    continue

                # Match by full anchor identity: symbol + line + is_assignment
                matching_overlay = None
                for overlay_anchor in panel._overlay_anchors:
                    if (overlay_anchor.symbol == anchor.symbol and
                        overlay_anchor.line == anchor.line and
                        overlay_anchor.is_assignment == anchor.is_assignment):
                        matching_overlay = overlay_anchor
                        break

                if matching_overlay is None:
                    continue

                # Forward data to this panel's plot as overlay
                plot = panel._plot

                # Add overlay data to the waveform or constellation plot
                from pyprobe.plugins.builtins.waveform import WaveformWidget
                from pyprobe.plugins.builtins.constellation import ConstellationWidget

                if plot is None or not isinstance(plot, (WaveformWidget, ConstellationWidget)):
                    # Buffer for later: plot widget not created yet or is still a
                    # placeholder type (e.g. ScalarHistoryChart) that will be replaced
                    # once the primary signal's data arrives and determines the final type.
                    panel_id = id(panel)
                    if panel_id not in self._pending_overlays:
                        self._pending_overlays[panel_id] = []
                    overlay_key = f"{anchor.symbol}_{'lhs' if anchor.is_assignment else 'rhs'}"
                    self._pending_overlays[panel_id].append({
                        'overlay_key': overlay_key,
                        'value': payload['value'],
                        'dtype': payload['dtype'],
                        'shape': payload.get('shape'),
                    })
                    logger.debug(f"Buffered overlay data for {anchor.symbol} (plot={type(plot).__name__ if plot else 'None'})")
                    continue

                # Use unique key that includes is_assignment to distinguish LHS/RHS
                overlay_key = f"{anchor.symbol}_{'lhs' if anchor.is_assignment else 'rhs'}"

                if isinstance(plot, WaveformWidget):
                    self._add_overlay_to_waveform(
                        plot,
                        matching_overlay,
                        payload['value'],
                        payload['dtype'],
                        payload.get('shape'),
                        primary_anchor=panel._anchor,
                        target_panel=panel
                    )
                elif isinstance(plot, ConstellationWidget):
                    self._add_overlay_to_constellation(
                        plot,
                        matching_overlay,
                        payload['value'],
                        payload['dtype'],
                        payload.get('shape'),
                        primary_anchor=panel._anchor,
                        target_panel=panel
                    )
    
    def flush_pending_overlays(self):
        """
        Apply any buffered overlay data to panels whose plot widgets now exist.
        
        Called after _maybe_redraw() / _force_redraw() which may create plot widgets.
        """
        if not self._pending_overlays:
            return
        
        from pyprobe.plugins.builtins.waveform import WaveformWidget
        from pyprobe.plugins.builtins.constellation import ConstellationWidget
        
        flushed_ids = []
        
        for panel_list in self._probe_panels.values():
            for panel in panel_list:
                if is_obj_deleted(panel):
                    continue
                panel_id = id(panel)
                if panel_id not in self._pending_overlays:
                    continue
                
                plot = panel._plot
                if plot is None:
                    continue  # Still not ready
                
                # Only flush if plot is now a supported overlay target type
                if not isinstance(plot, (WaveformWidget, ConstellationWidget)):
                    continue  # Plot still placeholder (e.g. ScalarHistoryChart), keep buffered
                
                # Apply all pending overlay data
                for pending in self._pending_overlays[panel_id]:
                    # Match pending key to an anchor in panel._overlay_anchors if possible
                    match_anchor = None
                    if hasattr(panel, '_overlay_anchors'):
                        for oa in panel._overlay_anchors:
                            key = f"{oa.symbol}_{'lhs' if oa.is_assignment else 'rhs'}"
                            if key == pending['overlay_key']:
                                match_anchor = oa
                                break
                    
                    if not match_anchor:
                        continue

                    if isinstance(plot, WaveformWidget):
                        self._add_overlay_to_waveform(
                            plot,
                            match_anchor,
                            pending['value'],
                            pending['dtype'],
                            pending['shape'],
                            primary_anchor=panel._anchor,
                            target_panel=panel
                        )
                    elif isinstance(plot, ConstellationWidget):
                        self._add_overlay_to_constellation(
                            plot,
                            match_anchor,
                            pending['value'],
                            pending['dtype'],
                            pending['shape'],
                            primary_anchor=panel._anchor,
                            target_panel=panel
                        )
                    logger.debug(f"Flushed pending overlay: {pending['overlay_key']}")
                
                flushed_ids.append(panel_id)
        
        # Clean up flushed entries
        for pid in flushed_ids:
            del self._pending_overlays[pid]
    def _add_overlay_to_waveform(
        self,
        plot,
        anchor: ProbeAnchor,
        value,
        dtype: str,
        shape,
        primary_anchor: Optional[ProbeAnchor] = None,
        target_panel: Optional[ProbePanel] = None
    ) -> None:
        """Add an overlay trace to a waveform plot."""
        import numpy as np
        import pyqtgraph as pg
        from PyQt6.QtCore import Qt
        
        # Support real and complex 1D arrays
        if dtype not in ('real_1d', 'complex_1d', 'array_collection', 'array_1d', 'array_complex'):
            return
        
        try:
            data = np.asarray(value)
            if data.ndim != 1:
                return  # Only 1D arrays supported for overlay
        except (ValueError, TypeError):
            return
        
        # Get or create overlay curves dict on the plot
        if not hasattr(plot, '_overlay_curves'):
            plot._overlay_curves = {}

        from pyprobe.gui.theme.theme_manager import ThemeManager
        theme = ThemeManager.instance().current
        theme_palette = list(theme.row_colors)
        marker_color = theme.colors.get('accent_marker', theme.plot_colors.get('marker', '#ffbf5f'))

        overlay_palette = [marker_color]
        overlay_palette.extend([c for c in theme_palette if c.lower() != marker_color.lower()])
        if not overlay_palette:
            overlay_palette = ['#ffbf5f', '#4fc3f7', '#6bd47a']
        
        trace_id = self._registry.get_trace_id(anchor) or ""
        symbol = anchor.symbol
        
        def on_legend_remove(item):
            # item might be a pg.PlotCurveItem or a pg.LegendItem.ItemSample
            actual_item = item
            if hasattr(item, "item"):
                actual_item = item.item

            # Find which anchor this item belongs to
            # First check primary curves
            if hasattr(plot, "_curves") and actual_item in plot._curves:
                if target_panel:
                    target_panel.close_requested.emit()
                return

            # Then check overlays
            for a, curves in getattr(plot, "_overlay_curves_by_anchor", {}).items():
                if actual_item in curves:
                    if target_panel:
                        target_panel.overlay_remove_requested.emit(target_panel, a)
                    return

        def ensure_legend():
            """Create legend on-demand and add primary curve if needed."""
            if not hasattr(plot, "_legend") or plot._legend is None:
                plot._legend = RemovableLegendItem(
                    offset=(10, 10),
                    labelTextColor=theme.colors.get("text_primary", "#ffffff"),
                    brush=pg.mkBrush(theme.colors.get("bg_medium", "#1a1a1a") + "80"),
                )
                plot._legend.setParentItem(plot._plot_widget.getPlotItem())
                plot._legend.trace_removal_requested.connect(on_legend_remove)

                # Add primary curve(s) to legend
                if hasattr(plot, "_curves") and plot._curves and primary_anchor:
                    p_id = self._registry.get_trace_id(primary_anchor) or ""
                    plot._legend.addItem(plot._curves[0], f"{p_id}: {plot._var_name}")

        # Track curves by anchor for removal lookup
        if not hasattr(plot, "_overlay_curves_by_anchor"):
            plot._overlay_curves_by_anchor = {}
        
        # Check if complex data
        is_complex = np.iscomplexobj(data) or dtype in ('complex_1d', 'array_complex')
        
        if is_complex:
            # Create real and imag curve keys
            # Use symbol + is_assignment to match forward_overlay_data logic
            symbol_key = f"{symbol}_{'lhs' if anchor.is_assignment else 'rhs'}"
            real_key = f"{symbol_key}_real"
            imag_key = f"{symbol_key}_imag"
            
            # Create real curve if needed
            if real_key not in plot._overlay_curves:
                color_idx = len(plot._overlay_curves) + 1
                color = overlay_palette[color_idx % len(overlay_palette)]
                curve = plot._plot_widget.plot(
                    pen=pg.mkPen(color=color, width=1.5),
                    antialias=False
                )
                curve.setZValue(20)
                plot._overlay_curves[real_key] = curve
                
                # Track for removal
                if anchor not in plot._overlay_curves_by_anchor:
                    plot._overlay_curves_by_anchor[anchor] = []
                plot._overlay_curves_by_anchor[anchor].append(curve)

                ensure_legend()
                plot._legend.addItem(curve, f"{trace_id}: {symbol} (real)")
            
            # Create imag curve if needed
            if imag_key not in plot._overlay_curves:
                color_idx = len(plot._overlay_curves) + 1
                color = overlay_palette[color_idx % len(overlay_palette)]
                curve = plot._plot_widget.plot(
                    pen=pg.mkPen(color=color, width=1.5, style=Qt.PenStyle.DashLine),
                    antialias=False
                )
                curve.setZValue(20)
                plot._overlay_curves[imag_key] = curve
                
                # Track for removal
                if anchor not in plot._overlay_curves_by_anchor:
                    plot._overlay_curves_by_anchor[anchor] = []
                plot._overlay_curves_by_anchor[anchor].append(curve)

                ensure_legend()
                plot._legend.addItem(curve, f"{trace_id}: {symbol} (imag)")
            
            # Update curve data
            real_data = data.real.copy()
            imag_data = data.imag.copy()
            x = np.arange(len(data))
            
            # Downsample if needed
            if len(data) > plot.MAX_DISPLAY_POINTS:
                real_data = plot.downsample(real_data)
                imag_data = plot.downsample(imag_data)
                x = np.arange(len(real_data))
            
            plot._overlay_curves[real_key].setData(x, real_data)
            plot._overlay_curves[imag_key].setData(x, imag_data)
        else:
            # Single real curve
            symbol_key = f"{symbol}_{'lhs' if anchor.is_assignment else 'rhs'}"
            if symbol_key not in plot._overlay_curves:
                color_idx = len(plot._overlay_curves) + 1
                color = overlay_palette[color_idx % len(overlay_palette)]
                curve = plot._plot_widget.plot(
                    pen=pg.mkPen(color=color, width=1.5),
                    antialias=False
                )
                curve.setZValue(20)
                plot._overlay_curves[symbol_key] = curve
                
                # Track for removal
                if anchor not in plot._overlay_curves_by_anchor:
                    plot._overlay_curves_by_anchor[anchor] = []
                plot._overlay_curves_by_anchor[anchor].append(curve)

                ensure_legend()
                plot._legend.addItem(curve, f"{trace_id}: {symbol}")
            
            # Update curve data
            x = np.arange(len(data))
            y = data
            if len(data) > plot.MAX_DISPLAY_POINTS:
                x, y = plot.downsample(data)
            
            plot._overlay_curves[symbol_key].setData(x, y)
    
    def _add_overlay_to_constellation(
        self,
        plot,
        anchor: ProbeAnchor,
        value,
        dtype: str,
        shape,
        primary_anchor: Optional[ProbeAnchor] = None,
        target_panel: Optional[ProbePanel] = None
    ) -> None:
        """Add an overlay scatter to a constellation plot."""
        import numpy as np
        import pyqtgraph as pg
        
        # Skip if not complex data
        if dtype not in ('complex_1d', 'array_complex', 'array_1d', 'waveform_complex'):
            return
        
        try:
            data = np.asarray(value).flatten()
            
            # Convert to complex if not already
            if not np.issubdtype(data.dtype, np.complexfloating):
                data = data.astype(np.complex128)
        except (ValueError, TypeError):
            return
        
        # Get or create overlay scatters dict on the plot
        if not hasattr(plot, "_overlay_scatters"):
            plot._overlay_scatters = {}

        if not hasattr(plot, "_overlay_scatters_by_anchor"):
            plot._overlay_scatters_by_anchor = {}

        from pyprobe.gui.theme.theme_manager import ThemeManager

        theme = ThemeManager.instance().current
        theme_palette = list(theme.row_colors)
        marker_color = theme.colors.get(
            "accent_marker", theme.plot_colors.get("marker", "#ffbf5f")
        )
        overlay_palette = [marker_color]
        overlay_palette.extend(
            [c for c in theme_palette if c.lower() != marker_color.lower()]
        )
        if not overlay_palette:
            overlay_palette = ["#ffbf5f", "#4fc3f7", "#6bd47a"]

        trace_id = self._registry.get_trace_id(anchor) or ""
        symbol = anchor.symbol
        symbol_key = f"{symbol}_{'lhs' if anchor.is_assignment else 'rhs'}"

        def on_legend_remove(item):
            # item might be a pg.ScatterPlotItem or a pg.LegendItem.ItemSample
            actual_item = item
            if hasattr(item, "item"):
                actual_item = item.item

            # Check primary scatters
            if hasattr(plot, "_scatter_items") and actual_item in plot._scatter_items:
                if target_panel:
                    target_panel.close_requested.emit()
                return

            # Check overlays
            for a, scatters in getattr(plot, "_overlay_scatters_by_anchor", {}).items():
                if actual_item in scatters:
                    if target_panel:
                        target_panel.overlay_remove_requested.emit(target_panel, a)
                    return

        def ensure_legend():
            if not hasattr(plot, "_legend") or plot._legend is None:
                plot._legend = RemovableLegendItem(
                    offset=(10, 10),
                    labelTextColor=theme.colors.get("text_primary", "#ffffff"),
                    brush=pg.mkBrush(theme.colors.get("bg_medium", "#1a1a1a") + "80"),
                )
                plot._legend.setParentItem(plot._plot_widget.getPlotItem())
                plot._legend.trace_removal_requested.connect(on_legend_remove)

                # Add primary scatter to legend
                if hasattr(plot, "_scatter_items") and plot._scatter_items and primary_anchor:
                    p_id = self._registry.get_trace_id(primary_anchor) or ""
                    plot._legend.addItem(
                        plot._scatter_items[-1], f"{p_id}: {plot._var_name}"
                    )

        if symbol_key not in plot._overlay_scatters:
            color_idx = len(plot._overlay_scatters) + 1
            color = overlay_palette[color_idx % len(overlay_palette)]

            # Create scatter for overlay
            scatter = pg.ScatterPlotItem(pen=None, brush=pg.mkBrush(color), size=5)
            plot._plot_widget.addItem(scatter)
            plot._overlay_scatters[symbol_key] = scatter

            # Track for removal
            if anchor not in plot._overlay_scatters_by_anchor:
                plot._overlay_scatters_by_anchor[anchor] = []
            plot._overlay_scatters_by_anchor[anchor].append(scatter)

            ensure_legend()
            plot._legend.addItem(scatter, f"{trace_id}: {symbol}")

        # Downsample and update
        display_data = plot.downsample(data)
        plot._overlay_scatters[symbol_key].setData(x=display_data.real, y=display_data.imag)
