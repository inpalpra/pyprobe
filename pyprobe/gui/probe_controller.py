"""
Probe lifecycle controller.

Extracted from MainWindow to separate concerns.
Handles: probe add/remove, lens preferences, overlay registration and rendering.
"""

from typing import Dict, Optional, List, Callable
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget
from PyQt6 import sip

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

    # StepRecorder-forwarded panel signals
    panel_lens_changed = pyqtSignal(object, str, str)  # (anchor, window_id, plugin_name)
    panel_park_requested = pyqtSignal(object)  # anchor
    panel_maximize_requested = pyqtSignal(object)  # anchor
    panel_color_changed = pyqtSignal(object, object)  # (anchor, QColor)
    panel_draw_mode_changed = pyqtSignal(object, str, str)  # (anchor, series_key, mode_name)
    panel_markers_cleared = pyqtSignal(object)  # anchor
    panel_trace_visibility_changed = pyqtSignal(object, str, str, bool)  # (anchor, window_id, trace_name, visible)
    panel_legend_moved = pyqtSignal(object, str)  # (anchor, window_id)
    panel_interaction_mode_changed = pyqtSignal(object, str, str)  # (anchor, window_id, mode_name)
    panel_view_reset_triggered = pyqtSignal(object, str)  # (anchor, window_id)
    panel_view_adjusted = pyqtSignal(object, str)  # (anchor, window_id)
    panel_view_interaction_triggered = pyqtSignal(object, str, str)  # (anchor, window_id, description)
    
    def __init__(
        self,
        registry,
        container,
        code_viewer,
        gutter,
        get_ipc: Callable,
        get_is_running: Callable,
        is_in_watch: Optional[Callable] = None,
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
            is_in_watch: Callable(anchor) -> bool, checks watch sidebar
            parent: Parent QObject
        """
        super().__init__(parent)
        self._registry = registry
        self._container = container
        self._code_viewer = code_viewer
        self._gutter = gutter
        self._get_ipc = get_ipc
        self._get_is_running = get_is_running
        self._is_in_watch = is_in_watch or (lambda a: False)
        
        # Probe panels by anchor - supports multiple panels per anchor via Ctrl+click
        self._probe_panels: Dict[ProbeAnchor, List[QWidget]] = {}
        
        # Probe metadata (lens preferences, dtype, overlay target)
        self._probe_metadata: Dict[ProbeAnchor, dict] = {}
        
        # Pending overlay data: buffered when panel._plot is None
        # Key: id(panel), Value: list of (overlay_key, payload) tuples
        self._pending_overlays: Dict[int, list] = {}

        # M2.5: Cache last known payload for every anchor to allow immediate re-render on lens change
        self._last_payloads: Dict[ProbeAnchor, dict] = {}
    
    @property
    def probe_panels(self) -> Dict[ProbeAnchor, List[QWidget]]:
        """Access to probe panels dict."""
        return self._probe_panels
    
    @property
    def probe_metadata(self) -> Dict[ProbeAnchor, dict]:
        """Access to probe metadata dict."""
        return self._probe_metadata

    def probe_trace_entries(self) -> list:
        """Return a list of ProbeTraceEntry for each active probe anchor."""
        from pyprobe.report.report_model import ProbeTraceEntry
        entries = []
        for anchor, meta in self._probe_metadata.items():
            raw_shape = meta.get('shape')
            shape: tuple = tuple(raw_shape) if raw_shape else ()
            entries.append(ProbeTraceEntry(
                symbol=anchor.symbol,
                file=anchor.file,
                line=anchor.line,
                column=anchor.col,
                shape=shape,
                dtype=meta.get('dtype') or 'unknown',
            ))
        return entries

    def is_used_as_overlay(self, anchor: ProbeAnchor) -> bool:
        """Check if anchor is currently used as an overlay on any active panel."""
        for panel_list in self._probe_panels.values():
            for panel in panel_list:
                if is_obj_deleted(panel) or getattr(panel, 'is_closing', False):
                    continue
                if hasattr(panel, '_overlay_anchors') and anchor in panel._overlay_anchors:
                    return True
        return False

    def has_active_panels(self, anchor: ProbeAnchor) -> bool:
        """Check if anchor has any non-deleted, non-closing panels."""
        for p in self._probe_panels.get(anchor, []):
            if not is_obj_deleted(p) and not getattr(p, 'is_closing', False):
                return True
        return False

    def handle_panel_closing(self, panel) -> None:
        """Clean up overlay highlights before a panel is closed.

        Called by ProbePanelContainer.panel_closing signal, before
        the panel is marked as is_closing.
        """
        if is_obj_deleted(panel):
            return
        overlay_anchors = getattr(panel, '_overlay_anchors', None)
        if not overlay_anchors:
            return

        logger.debug(f"Cleaning up {len(overlay_anchors)} overlay(s) for closing panel")

        for overlay_anchor in list(overlay_anchors):
            # Check if any OTHER panel still uses this overlay
            anchor_still_used = False
            for panel_list in self._probe_panels.values():
                for p in panel_list:
                    if p is panel or is_obj_deleted(p) or getattr(p, 'is_closing', False):
                        continue
                    if hasattr(p, '_overlay_anchors') and overlay_anchor in p._overlay_anchors:
                        anchor_still_used = True
                        break
                if anchor_still_used:
                    break

            if not anchor_still_used:
                # Decrement highlight ref count
                self._code_viewer.remove_probe(overlay_anchor)

                # Full cleanup for overlay-only probes
                has_panels = self.has_active_panels(overlay_anchor)
                in_watch = self._is_in_watch(overlay_anchor)
                if not has_panels and not in_watch:
                    meta = self._probe_metadata.get(overlay_anchor)
                    is_overlay_only = meta and meta.get('overlay_target')
                    if is_overlay_only:
                        self._registry.remove_probe(overlay_anchor)
                        line_still_probed = any(
                            a.line == overlay_anchor.line and a != overlay_anchor
                            for a in self._registry.active_anchors
                        )
                        if not line_still_probed:
                            self._gutter.clear_probed_line(overlay_anchor.line)
                        if overlay_anchor in self._probe_metadata:
                            del self._probe_metadata[overlay_anchor]
                        ipc = self._get_ipc()
                        if ipc and self._get_is_running():
                            msg = make_remove_probe_cmd(overlay_anchor)
                            ipc.send_command(msg)

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

        # Clean stale (deleted/closing) panels before checking
        if anchor in self._probe_panels:
            self._probe_panels[anchor] = [
                p for p in self._probe_panels[anchor]
                if not is_obj_deleted(p) and not getattr(p, 'is_closing', False)
            ]
            if not self._probe_panels[anchor]:
                del self._probe_panels[anchor]

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
        
        # Unified Lens Change Handling
        dropdown = getattr(panel, '_lens_dropdown', None)
        if dropdown is not None:
            dropdown.lens_changed.connect(
                lambda name, p=panel, a=anchor: self._handle_lens_changed_internal(a, p, name)
            )
            
            # Use explicit lens_name if provided, otherwise check stored metadata
            lens_to_apply = lens_name or self._probe_metadata[anchor].get('lens')
            if lens_to_apply:
                if not dropdown.set_lens(lens_to_apply):
                    # Dropdown has no compatible plugins yet (no data); defer
                    panel._pending_lens = lens_to_apply
        
        # Connect color changed signal
        panel.color_changed.connect(self._on_probe_color_changed)

        # Forward per-panel signals for StepRecorder
        panel.park_requested.connect(lambda a=anchor: self.panel_park_requested.emit(a))
        panel.maximize_requested.connect(lambda a=anchor: self.panel_maximize_requested.emit(a))
        panel.color_changed.connect(lambda a, c: self.panel_color_changed.emit(a, c))
        panel.draw_mode_changed.connect(
            lambda key, mode, a=anchor: self.panel_draw_mode_changed.emit(a, key, mode)
        )
        panel.markers_cleared.connect(lambda a=anchor: self.panel_markers_cleared.emit(a))

        # Forward legend toggle signal for StepRecorder
        panel.legend_trace_toggled.connect(
            lambda name, visible, a=anchor, p=panel: self.panel_trace_visibility_changed.emit(a, p.window_id, name, visible)
        )
        panel.legend_moved.connect(
            lambda a=anchor, p=panel: self.panel_legend_moved.emit(a, p.window_id)
        )

        # Forward interaction mode and view signals for StepRecorder
        panel.interaction_mode_changed.connect(
            lambda mode, a=anchor, p=panel: self.panel_interaction_mode_changed.emit(a, p.window_id, mode)
        )
        panel.view_reset_triggered.connect(
            lambda a=anchor, p=panel: self.panel_view_reset_triggered.emit(a, p.window_id)
        )
        panel.view_adjusted.connect(
            lambda a=anchor, p=panel: self.panel_view_adjusted.emit(a, p.window_id)
        )
        panel.view_interaction_triggered.connect(
            lambda desc, a=anchor, p=panel: self.panel_view_interaction_triggered.emit(a, p.window_id, desc)
        )

        # Send to runner if running
        ipc = self._get_ipc()
        if ipc and self._get_is_running():
            msg = make_add_probe_cmd(anchor)
            ipc.send_command(msg)
        
        self.status_message.emit(f"Probe added: {anchor.identity_label()}")
        self.probe_added.emit(anchor, panel)
        
        return panel

    def _handle_lens_changed_internal(self, anchor: ProbeAnchor, panel, lens_name: str):
        """Unified internal handler for lens changes."""
        # 1. Update metadata
        if anchor in self._probe_metadata:
            self._probe_metadata[anchor]['lens'] = lens_name
        
        # 2. Re-apply cached overlay data immediately so secondary traces don't disappear
        if hasattr(panel, '_overlay_anchors'):
            from PyQt6.QtCore import QTimer
            for ov_anchor in panel._overlay_anchors:
                payload = self._last_payloads.get(ov_anchor)
                if payload:
                    # Delay slightly to ensure the new plot widget is fully initialized 
                    # and its layout is settled (similar to primary trace re-apply)
                    QTimer.singleShot(0, lambda a=ov_anchor, p=payload: self.forward_overlay_data(a, p))

        # 3. Emit signal for StepRecorder
        self.panel_lens_changed.emit(anchor, panel.window_id, lens_name)

    def _on_probe_color_changed(self, anchor: ProbeAnchor, color: QColor) -> None:
        """Handle color change from a probe panel — update registry, code viewer and all other panels."""
        # 1. Update central registry so any FUTURE panels/overlays use this color
        self._registry.set_color(anchor, color)
        
        # 2. Update Code Viewer and Gutter
        self._code_viewer.update_probe_color(anchor, color)
        self._gutter.set_probed_line(anchor.line, color)
        
        # 3. Update ALL other panels for this anchor to maintain consistency
        if anchor in self._probe_panels:
            for panel in self._probe_panels[anchor]:
                if is_obj_deleted(panel):
                    continue
                # Block signals to prevent infinite recursion loop
                panel.blockSignals(True)
                # This updates the panel identity label and its internal _plot widget
                if hasattr(panel, '_color') and panel._color != color:
                    panel._color = color
                    # Duplicate logic from ProbePanel._change_probe_color but without emitting signal again
                    hex_color = color.name()
                    if hasattr(panel, '_identity_label'):
                        panel._identity_label.setStyleSheet(f"QLabel {{ color: {hex_color}; font-size: 11px; font-weight: bold; }}")
                    if panel._plot and hasattr(panel._plot, 'set_color'):
                        panel._plot.set_color(color)
                panel.blockSignals(False)
    
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
            if not is_obj_deleted(panel):
                self._container.remove_probe_panel(panel=panel)

            # If no more panels for this anchor, remove from internal list
            if not panel_list:
                del self._probe_panels[anchor]
                logger.debug("No more panels for this anchor in controller")

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
            # Increment highlight ref count if this is the first overlay usage,
            # so removing the standalone panel won't drop the highlight
            if not self.is_used_as_overlay(overlay_anchor):
                color = self._registry.get_color(overlay_anchor)
                if color:
                    self._code_viewer.set_probe_active(overlay_anchor, color)
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
        if is_obj_deleted(target_panel) or target_panel.is_closing:
            logger.warning("Attempted to add overlay to a deleted or closing panel")
            return

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
        if is_obj_deleted(target_panel) or target_panel.is_closing:
            logger.debug("Skipping remove_overlay for a deleted or closing panel")
            return

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

        if not anchor_still_used:
            # Decrement the overlay ref count that was added by handle_overlay_requested
            self._code_viewer.remove_probe(overlay_anchor)

            has_panels = self.has_active_panels(overlay_anchor)
            in_watch = self._is_in_watch(overlay_anchor)

            # Only do full cleanup if not used anywhere else
            if not has_panels and not in_watch:
                meta = self._probe_metadata.get(overlay_anchor)
                is_overlay_only = meta and meta.get('overlay_target')

                if is_overlay_only:
                    self._registry.remove_probe(overlay_anchor)
                    # Only clear gutter if no other active probes on same line
                    line_still_probed = any(
                        a.line == overlay_anchor.line and a != overlay_anchor
                        for a in self._registry.active_anchors
                    )
                    if not line_still_probed:
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
        # Cache for immediate re-rendering on lens change
        self._last_payloads[anchor] = payload

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
                from pyprobe.plugins.builtins.complex_plots import ComplexWidget
                from pyprobe.plugins.builtins.constellation import ConstellationWidget

                if plot is None or not isinstance(plot, (WaveformWidget, ComplexWidget, ConstellationWidget)):
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

                if isinstance(plot, ConstellationWidget):
                    self._add_overlay_to_constellation(
                        plot,
                        matching_overlay,
                        payload['value'],
                        payload['dtype'],
                        payload.get('shape'),
                        primary_anchor=panel._anchor,
                        target_panel=panel
                    )
                elif isinstance(plot, (WaveformWidget, ComplexWidget)):
                    self._add_overlay_to_waveform(
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
        from pyprobe.plugins.builtins.complex_plots import ComplexWidget
        
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
                if not isinstance(plot, (WaveformWidget, ComplexWidget)):
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

                    if isinstance(plot, (WaveformWidget, ComplexWidget)):
                        self._add_overlay_to_waveform(
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
        
        # Get consistent color from registry for this anchor
        reg_color = self._registry.get_color(anchor)
        reg_color_hex = reg_color.name() if reg_color else None

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
            """Create legend on-demand or upgrade existing one to RemovableLegendItem."""
            existing = getattr(plot, "_legend", None)
            
            # If no legend or standard pg.LegendItem, (re)create as RemovableLegendItem
            if existing is None or type(existing) == pg.LegendItem:
                if existing is not None:
                    try:
                        existing.scene().removeItem(existing)
                    except Exception:
                        pass
                
                plot._legend = RemovableLegendItem(
                    offset=(10, 10),
                    labelTextColor=theme.colors.get("text_primary", "#ffffff"),
                    brush=pg.mkBrush(theme.colors.get("bg_medium", "#1a1a1a") + "80"),
                )
                plot._legend.setParentItem(plot._plot_widget.getPlotItem())
                plot._legend.trace_removal_requested.connect(on_legend_remove)
                
                # Forward visibility changes for StepRecorder
                def on_visibility_changed(item, visible, p=target_panel):
                    # Find label for this item
                    label_text = "Unknown"
                    for i, label in plot._legend.items:
                        if i == item or (hasattr(i, 'item') and i.item == item):
                            label_text = label.text
                            break
                    self.panel_trace_visibility_changed.emit(
                        primary_anchor, p.window_id, label_text, visible
                    )
                plot._legend.trace_visibility_changed.connect(on_visibility_changed)
                if hasattr(plot._legend, 'legend_moved'):
                    plot._legend.legend_moved.connect(target_panel.legend_moved)

        # Track curves by anchor for removal lookup
        if not hasattr(plot, "_overlay_curves_by_anchor"):
            plot._overlay_curves_by_anchor = {}
        
        # Use trace_id in key to ensure uniqueness if multiple anchors have same symbol
        symbol_key = f"{trace_id}_{symbol}_{'lhs' if anchor.is_assignment else 'rhs'}"
        
        # Check if complex data
        is_complex = np.iscomplexobj(data) or dtype in ('complex_1d', 'array_complex')
        
        if is_complex:
            # Create real and imag curve keys
            real_key = f"{symbol_key}_real"
            imag_key = f"{symbol_key}_imag"
            
            # Create real curve if needed
            if real_key not in plot._overlay_curves:
                color_idx = len(plot._overlay_curves) + 1
                # Use registry color if available, fallback to palette
                color = reg_color_hex if reg_color_hex else overlay_palette[color_idx % len(overlay_palette)]
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
                # Use registry color if available, fallback to palette
                color = reg_color_hex if reg_color_hex else overlay_palette[color_idx % len(overlay_palette)]
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
            if symbol_key not in plot._overlay_curves:
                color_idx = len(plot._overlay_curves) + 1
                # Use registry color if available, fallback to palette
                color = reg_color_hex if reg_color_hex else overlay_palette[color_idx % len(overlay_palette)]
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

        # Get consistent color from registry for this anchor
        reg_color = self._registry.get_color(anchor)
        reg_color_hex = reg_color.name() if reg_color else None

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
            """Create legend on-demand or upgrade existing one to RemovableLegendItem."""
            existing = getattr(plot, "_legend", None)
            
            # If no legend or standard pg.LegendItem, (re)create as RemovableLegendItem
            if existing is None or type(existing) == pg.LegendItem:
                if existing is not None:
                    try:
                        existing.scene().removeItem(existing)
                    except Exception:
                        pass
                
                plot._legend = RemovableLegendItem(
                    offset=(10, 10),
                    labelTextColor=theme.colors.get("text_primary", "#ffffff"),
                    brush=pg.mkBrush(theme.colors.get("bg_medium", "#1a1a1a") + "80"),
                )
                plot._legend.setParentItem(plot._plot_widget.getPlotItem())
                plot._legend.trace_removal_requested.connect(on_legend_remove)
                
                # Forward visibility changes for StepRecorder
                def on_visibility_changed(item, visible, p=target_panel):
                    # Find label for this item
                    label_text = "Unknown"
                    for i, label in plot._legend.items:
                        if i == item or (hasattr(i, 'item') and i.item == item):
                            label_text = label.text
                            break
                    self.panel_trace_visibility_changed.emit(
                        primary_anchor, p.window_id, label_text, visible
                    )
                plot._legend.trace_visibility_changed.connect(on_visibility_changed)
                if hasattr(plot._legend, 'legend_moved'):
                    plot._legend.legend_moved.connect(target_panel.legend_moved)

        # Use trace_id in key to ensure uniqueness if multiple anchors have same symbol
        symbol_key = f"{trace_id}_{symbol}_{'lhs' if anchor.is_assignment else 'rhs'}"

        if symbol_key not in plot._overlay_scatters:
            color_idx = len(plot._overlay_scatters) + 1
            # Use registry color if available, fallback to palette
            color = reg_color_hex if reg_color_hex else overlay_palette[color_idx % len(overlay_palette)]

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
