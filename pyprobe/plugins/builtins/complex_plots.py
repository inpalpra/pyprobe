from typing import Any, Optional, Tuple, List, Dict
import time
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QRectF, QTimer, pyqtSignal, QPointF

from ..base import ProbePlugin
from ...core.data_classifier import (
    DTYPE_ARRAY_COMPLEX, DTYPE_WAVEFORM_COMPLEX, get_waveform_info
)
from ...plots.axis_controller import AxisController
from ...plots.pin_indicator import PinIndicator
from ...plots.draw_mode import DrawMode, apply_draw_mode
from ...plots.editable_axis import EditableAxisItem
from ...gui.axis_editor import AxisEditor
from ...plots.marker_model import MarkerStore
from ...plots.marker_items import MarkerOverlay, MarkerGlyph, snap_to_nearest

MAX_DISPLAY_POINTS = 5000

def downsample(data: np.ndarray, n_points: int = 0, x_offset: int = 0) -> tuple:
    """Downsample large data for display, returning (x_indices, y_values).
    
    Uses min-max decimation: the array is split into chunks and each chunk
    contributes its (argmin, min) and (argmax, max) pair, preserving the
    visual envelope.  Chunk boundaries are computed with linspace so the
    full array [0, N) is always covered — no tail samples are dropped.
    """
    if n_points <= 0:
        n_points = MAX_DISPLAY_POINTS

    n = len(data)
    if n <= n_points:
        return np.arange(n) + x_offset, data
    
    n_chunks = n_points // 2
    # Boundaries always span [0, n] — no remainder
    edges = np.linspace(0, n, n_chunks + 1, dtype=int)
    
    x = np.empty(n_chunks * 2, dtype=np.int64)
    y = np.empty(n_chunks * 2, dtype=data.dtype)
    
    for i in range(n_chunks):
        chunk = data[edges[i]:edges[i + 1]]
        amin = int(np.argmin(chunk))
        amax = int(np.argmax(chunk))
        # Always emit (lower_index, upper_index) order so the line is monotonic in x
        lo, hi = sorted([amin, amax])
        x[2 * i]     = edges[i] + lo + x_offset
        x[2 * i + 1] = edges[i] + hi + x_offset
        y[2 * i]     = chunk[lo]
        y[2 * i + 1] = chunk[hi]
    
    return x, y

# ── SI-prefix formatter (shared by ComplexWidget and WaveformWidget) ──
_SI_PREFIXES = [
    (1e15,  'P'),
    (1e12,  'T'),
    (1e9,   'G'),
    (1e6,   'M'),
    (1e3,   'k'),
    (1e0,   ''),
    (1e-3,  'm'),
    (1e-6,  'µ'),
    (1e-9,  'n'),
    (1e-12, 'p'),
    (1e-15, 'f'),
]

def format_coord(val: float) -> str:
    """Format a value using SI prefixes with 6 decimal places.

    Falls back to scientific notation for |val| > 1e15 or < 1e-15.
    """
    if val == 0:
        return '0.000000'
    av = abs(val)
    if av >= 1e15 or av < 1e-15:
        return f'{val:.6e}'
    for threshold, prefix in _SI_PREFIXES:
        if av >= threshold:
            return f'{val / threshold:.6f}{prefix}'
    return f'{val:.6e}'


class ComplexWidget(QWidget):
    """Base widget for complex time-domain plots with zoom-responsive downsampling."""

    status_message_requested = pyqtSignal(str)
    MAX_DISPLAY_POINTS = 5000
    
    def __init__(self, var_name: str, color: QColor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._var_name = var_name
        self._color = color
        self._plot_widget = pg.PlotWidget()
        self._info_label = QLabel("")
        self._raw_data: Optional[np.ndarray] = None  # Raw complex array
        self._t_vector: Optional[np.ndarray] = None  # X-axis from waveform metadata
        
        # Axis pinning
        self._axis_controller: Optional[AxisController] = None
        self._pin_indicator: Optional[PinIndicator] = None
        self._axis_editor: Optional[AxisEditor] = None
        
        # Per-series draw mode: series_key -> DrawMode
        self._draw_modes: Dict[str, DrawMode] = {}
        # Series key -> (curve, color_hex) for apply_draw_mode
        self._series_curves: Dict[str, tuple] = {}
        
        # Zoom-responsive state
        self._zoom_timer = QTimer()
        self._zoom_timer.setSingleShot(True)
        self._zoom_timer.setInterval(50)
        self._zoom_timer.timeout.connect(self._rerender_for_zoom)
        self._updating_curves = False
        
        # M2.5: Overlay tracking
        self._overlay_curves: Dict[str, pg.PlotDataItem] = {}
        self._overlay_curves_by_anchor: Dict[ProbeAnchor, List[pg.PlotDataItem]] = {}
        
        self._setup_ui()
        self._configure_plot()

        from ...gui.theme.theme_manager import ThemeManager
        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.current)

    def downsample(self, data: np.ndarray, n_points: int = 5000, x_offset: int = 0) -> Tuple[np.ndarray, np.ndarray]:
        """Delegate to global downsample function."""
        return downsample(data, n_points, x_offset)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        header = QHBoxLayout()
        self._name_label = QLabel(self._var_name)
        self._name_label.setFont(QFont("JetBrains Mono", 11, QFont.Weight.Bold))
        self._name_label.setStyleSheet(f"color: {self._color.name()};")
        header.addWidget(self._name_label)
        header.addStretch()
        
        self._info_label.setFont(QFont("JetBrains Mono", 9))
        self._info_label.setStyleSheet("color: #888888;")
        header.addWidget(self._info_label)
        layout.addLayout(header)
        
        layout.addWidget(self._plot_widget)

        # Footer spacer to make room for the hover toolbar (matching WaveformWidget's layout)
        self._footer_spacer = QLabel("")
        self._footer_spacer.setFixedHeight(24)
        layout.addWidget(self._footer_spacer)

    def _configure_plot(self):
        self._plot_widget.setBackground('#0d0d0d')
        # Use a more visible default grid alpha (0.6) before theme override
        self._plot_widget.showGrid(x=True, y=True, alpha=0.6)
        
        # Use RemovableLegendItem for StepRecorder compatibility
        from pyprobe.gui.probe_panel import RemovableLegendItem
        from pyprobe.gui.theme.theme_manager import ThemeManager
        theme_colors = ThemeManager.instance().current.colors
        self._legend = RemovableLegendItem(
            offset=(10, 10),
            labelTextColor=theme_colors.get('text_primary', '#ffffff'),
            brush=pg.mkBrush(theme_colors.get('bg_medium', '#1a1a1a') + '80')
        )
        self._legend.setParentItem(self._plot_widget.getPlotItem())
        
        # Setup editable axes
        self._setup_editable_axes()
        
        # Add bottom label after replacing axes
        self._plot_widget.setLabel('bottom', 'Sample Index')
        
        # Axis editor (inline text editor)
        self._axis_editor = AxisEditor(self._plot_widget)
        self._axis_editor.value_committed.connect(self._on_axis_value_committed)
        self._axis_editor.editing_cancelled.connect(self._on_axis_edit_cancelled)
        
        # Setup axis controller and pin indicator
        plot_item = self._plot_widget.getPlotItem()
        self._axis_controller = AxisController(plot_item)
        self._axis_controller.pin_state_changed.connect(self._on_pin_state_changed)

        self._pin_indicator = PinIndicator(self)
        self._pin_indicator.x_pin_clicked.connect(lambda: self._axis_controller.toggle_pin('x'))
        self._pin_indicator.y_pin_clicked.connect(lambda: self._axis_controller.toggle_pin('y'))
        self._pin_indicator.raise_()
        self._pin_indicator.show()

        # Zoom-responsive: connect sigRangeChanged
        vb = plot_item.getViewBox()
        vb.sigRangeChanged.connect(self._on_view_range_changed)

        # Mouse hover coordinate display
        self._plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)
        
        # M3: Marker System
        self._marker_store = MarkerStore(self)
        self._marker_overlay = MarkerOverlay(self._plot_widget)
        self._marker_store.markers_changed.connect(self._refresh_markers)
        self._marker_overlay.marker_removed_requested.connect(self._marker_store.remove_marker)
        self._marker_glyphs = {}
        
        self._plot_widget.scene().sigMouseClicked.connect(self._on_mouse_clicked)

    def _apply_theme(self, theme) -> None:
        c = theme.colors
        pc = theme.plot_colors
        grid_alpha = float(pc.get('grid_alpha', 0.28))
        self._plot_widget.setBackground(pc['bg'])
        self._plot_widget.showGrid(x=True, y=True, alpha=grid_alpha)
        self._info_label.setStyleSheet(f"color: {c['text_secondary']};")
        
        # manually force grid
        alpha_int = int(min(255, max(0, grid_alpha * 255)))
        axis_pen = pg.mkPen(color=pc['axis'], width=1)
        for ax_name in ('left', 'bottom', 'right'):
            ax = self._plot_widget.getAxis(ax_name)
            if ax is not None:
                ax.setPen(axis_pen)
                ax.setTextPen(axis_pen)
                if hasattr(ax, 'setGrid'):
                    ax.setGrid(alpha_int)

    def update_info(self, text: str):
        self._info_label.setText(text)

    # === Editable Axes ===
    
    def _setup_editable_axes(self) -> None:
        """Replace standard axes with editable ones that support double-click editing."""
        plot_item = self._plot_widget.getPlotItem()

        # Create editable axes
        bottom_axis = EditableAxisItem('bottom')
        left_axis = EditableAxisItem('left')

        # Style them to match probe color
        axis_pen = pg.mkPen(color=self._color.name(), width=1)
        bottom_axis.setPen(axis_pen)
        bottom_axis.setTextPen(axis_pen)
        left_axis.setPen(axis_pen)
        left_axis.setTextPen(axis_pen)

        # Place axes (and their grids) above the plotted data
        bottom_axis.setZValue(10)
        left_axis.setZValue(10)

        # Replace existing axes
        plot_item.setAxisItems({'bottom': bottom_axis, 'left': left_axis})

        # Explicitly set grid on current editable axes
        bottom_axis.setGrid(153) # ~0.6 alpha
        left_axis.setGrid(153)

        # Connect edit signals
        bottom_axis.edit_min_requested.connect(lambda val: self._start_axis_edit('x', 'min', val))
        bottom_axis.edit_max_requested.connect(lambda val: self._start_axis_edit('x', 'max', val))
        left_axis.edit_min_requested.connect(lambda val: self._start_axis_edit('y', 'min', val))
        left_axis.edit_max_requested.connect(lambda val: self._start_axis_edit('y', 'max', val))

    def _setup_editable_secondary_axis(self, secondary_color: str, label: str = '') -> None:
        """Replace the right axis with an EditableAxisItem for double-click editing.

        Must be called *after* `_p1`, `_p2`, and `showAxis('right')` are set up.
        """
        right_axis = EditableAxisItem('right')
        axis_pen = pg.mkPen(color=secondary_color, width=1)
        right_axis.setPen(axis_pen)
        right_axis.setTextPen(axis_pen)
        right_axis.setZValue(10)

        # Replace the existing right axis and re-link to secondary ViewBox
        self._p1.setAxisItems({'right': right_axis})
        right_axis.linkToView(self._p2)
        if label:
            right_axis.setLabel(label, color=secondary_color)

        # Wire signals — use 'y2' to distinguish from primary 'y'
        right_axis.edit_min_requested.connect(lambda val: self._start_axis_edit('y2', 'min', val))
        right_axis.edit_max_requested.connect(lambda val: self._start_axis_edit('y2', 'max', val))

    def _start_axis_edit(self, axis: str, endpoint: str, current_value: float) -> None:
        """Start inline editing of an axis min/max value."""
        if self._axis_editor is None:
            return

        # Store context for commit
        self._axis_editor.setProperty('edit_axis', axis)
        self._axis_editor.setProperty('edit_endpoint', endpoint)

        # Position near the axis
        if axis == 'x':
            x = 40 if endpoint == 'min' else self._plot_widget.width() - 60
            y = self._plot_widget.height() - 20
        elif axis == 'y2':
            # Right side of the plot
            x = self._plot_widget.width() - 20
            y = self._plot_widget.height() - 40 if endpoint == 'min' else 20
        else:
            x = 20
            y = self._plot_widget.height() - 40 if endpoint == 'min' else 20

        self._axis_editor.show_at(x, y, current_value)

    def _on_axis_value_committed(self, value: float) -> None:
        """Handle axis editor value committed."""
        axis = self._axis_editor.property('edit_axis')
        endpoint = self._axis_editor.property('edit_endpoint')
        plot_item = self._plot_widget.getPlotItem()
        view_box = plot_item.getViewBox()

        if axis == 'x':
            current_range = view_box.viewRange()[0]
            if endpoint == 'min':
                plot_item.setXRange(value, current_range[1], padding=0)
            else:
                plot_item.setXRange(current_range[0], value, padding=0)
            if self._axis_controller:
                self._axis_controller.set_pinned('x', True)
        elif axis == 'y':
            current_range = view_box.viewRange()[1]
            if endpoint == 'min':
                plot_item.setYRange(value, current_range[1], padding=0)
            else:
                plot_item.setYRange(current_range[0], value, padding=0)
            if self._axis_controller:
                self._axis_controller.set_pinned('y', True)
        elif axis == 'y2' and hasattr(self, '_p2'):
            current_range = self._p2.viewRange()[1]
            if endpoint == 'min':
                self._p2.setYRange(value, current_range[1], padding=0)
            else:
                self._p2.setYRange(current_range[0], value, padding=0)
            if self._axis_controller:
                self._axis_controller.set_pinned('y', True)

    def _on_axis_edit_cancelled(self) -> None:
        """Handle axis editor cancelled. Nothing to do."""
        pass

    def _register_series(self, key: str, curve, color_hex: str) -> None:
        """Register a named series for draw mode control."""
        self._draw_modes[key] = DrawMode.LINE
        self._series_curves[key] = (curve, color_hex)

    def set_color(self, color: QColor) -> None:
        """Update the primary probe color (name label + axis pens)."""
        self._color = color
        hex_color = color.name()
        self._name_label.setStyleSheet(f"color: {hex_color};")
        axis_pen = pg.mkPen(color=hex_color, width=1)
        for ax_name in ('left', 'bottom'):
            ax = self._plot_widget.getAxis(ax_name)
            if ax is not None:
                ax.setPen(axis_pen)
                ax.setTextPen(axis_pen)

    def set_series_color(self, series_key: str, color: QColor) -> None:
        """Change the color of a specific registered series."""
        if series_key not in self._series_curves:
            return
        hex_color = color.name()
        curve, _old_hex = self._series_curves[series_key]
        curve.setPen(pg.mkPen(hex_color, width=1.5))
        self._series_curves[series_key] = (curve, hex_color)
        # Re-apply draw mode with new color
        mode = self._draw_modes.get(series_key, DrawMode.LINE)
        apply_draw_mode(curve, mode, hex_color)

    def set_draw_mode(self, series_key: str, mode: DrawMode) -> None:
        """Set the draw mode for a named series."""
        if series_key not in self._series_curves:
            return
        self._draw_modes[series_key] = mode
        curve, color_hex = self._series_curves[series_key]
        apply_draw_mode(curve, mode, color_hex)

    def get_draw_mode(self, series_key: str) -> DrawMode:
        """Get the current draw mode for a named series."""
        return self._draw_modes.get(series_key, DrawMode.LINE)

    @property
    def series_keys(self) -> list:
        """Return the list of registered series keys."""
        return list(self._draw_modes.keys())

    def _on_pin_state_changed(self, axis: str, is_pinned: bool) -> None:
        """Handle axis pin state change from AxisController."""
        if self._pin_indicator:
            self._pin_indicator.update_state(axis, is_pinned)

    @property
    def axis_controller(self) -> Optional[AxisController]:
        """Access the axis controller for external use."""
        return self._axis_controller

    def showEvent(self, event) -> None:
        """Trigger layout update when widget is shown."""
        super().showEvent(event)
        QTimer.singleShot(0, self._update_pin_layout)

    def resizeEvent(self, event) -> None:
        """Reposition pin indicator on resize."""
        super().resizeEvent(event)
        self._update_pin_layout()
        if hasattr(self, '_marker_overlay'):
            self._marker_overlay._reposition()

    def _update_pin_layout(self) -> None:
        """Update the position of pin indicators relative to plot area."""
        if self._pin_indicator and self._plot_widget:
            self._pin_indicator.setGeometry(0, 0, self.width(), self.height())
            
            plot_item = self._plot_widget.getPlotItem()
            
            def get_mapped_rect(item):
                scene_rect = item.sceneBoundingRect()
                view_poly = self._plot_widget.mapFromScene(scene_rect)
                view_rect = view_poly.boundingRect()
                tl_mapped = self._plot_widget.mapTo(self, view_rect.topLeft())
                return QRectF(
                    float(tl_mapped.x()), float(tl_mapped.y()),
                    view_rect.width(), view_rect.height()
                )

            view_rect = get_mapped_rect(plot_item.getViewBox())
            self._pin_indicator.update_layout(view_rect)
            self._pin_indicator.raise_()

    # ── Zoom-responsive downsampling ──────────────────────

    def _on_view_range_changed(self, vb, ranges):
        """Handle view range changes — debounce and re-render."""
        if self._updating_curves or self._raw_data is None:
            return
        self._zoom_timer.start()

    def _render_slice(self, i_min: int, i_max: int):
        """Override in subclasses to re-render the visible slice."""
        pass
        
    def _rerender_for_zoom(self):
        """Re-downsample or show raw data based on visible x-range."""
        if self._raw_data is None:
            return
        vb = self._plot_widget.getPlotItem().getViewBox()
        x_min, x_max = vb.viewRange()[0]
        n = len(self._raw_data)
        
        # Map x-range to sample indices using t_vector if available
        if self._t_vector is not None and len(self._t_vector) == n:
            import bisect
            i_min = max(0, bisect.bisect_left(self._t_vector, x_min))
            i_max = min(n, bisect.bisect_right(self._t_vector, x_max))
        else:
            i_min = max(0, int(np.floor(x_min)))
            i_max = min(n, int(np.ceil(x_max)) + 1)
        if i_min >= i_max:
            return
        self._updating_curves = True
        self._render_slice(i_min, i_max)
        self._updating_curves = False
        self._refresh_markers()

    def _get_x_for_indices(self, indices: np.ndarray) -> np.ndarray:
        """Map sample indices to x-axis values using _t_vector if available."""
        if self._t_vector is not None and len(self._t_vector) > 0:
            return self._t_vector[indices]
        return indices.astype(float)

    def reset_view(self) -> None:
        """Reset the view: restore full data to curves, unpin axes, snap to full range."""
        if self._raw_data is None:
            return
        # Restore full dataset to curves via subclass _render_slice
        n = len(self._raw_data)
        self._updating_curves = True
        self._render_slice(0, n)
        self._updating_curves = False
        # Unpin axes and snap to full range
        if self._axis_controller:
            self._axis_controller.set_pinned('x', False)
            self._axis_controller.set_pinned('y', False)
        vb = self._plot_widget.getPlotItem().getViewBox()
        vb.autoRange(padding=0)
        self._refresh_markers()

    # ── Mouse hover coordinate helpers ─────────────────────

    def _get_active_viewbox(self):
        """Return the viewbox to use for coordinate mapping.

        For dual-axis subclasses (ComplexMAWidget, ComplexFftMagAngleWidget),
        prefer the primary (magnitude) ViewBox. Fall back to the secondary
        (phase) ViewBox only when all magnitude curves are hidden.
        """
        primary_vb = self._plot_widget.plotItem.vb
        # Check if we have a secondary viewbox (_p2)
        if hasattr(self, '_p2'):
            # Check if mag curve is visible
            if hasattr(self, '_mag_curve') and not self._mag_curve.isVisible():
                return self._p2
        return primary_vb

    def _on_mouse_moved(self, pos):
        """Format hover coordinates and emit status_message_requested."""
        vb = self._get_active_viewbox()
        mouse_point = vb.mapSceneToView(pos)
        x_str = format_coord(mouse_point.x())
        y_str = format_coord(mouse_point.y())
        self.status_message_requested.emit(f"X: {x_str},  Y: {y_str}")

    def leaveEvent(self, event):
        """Clear status bar when mouse leaves the plot widget."""
        super().leaveEvent(event)
        self.status_message_requested.emit("")

    def _on_mouse_clicked(self, ev):
        if ev.modifiers() == Qt.KeyboardModifier.AltModifier and ev.button() == Qt.MouseButton.LeftButton:
            ev.accept()
            curve_dict = {key: curve for key, (curve, _) in self._series_curves.items()}
            # Build per-curve ViewBox mapping for secondary-axis curves
            curve_viewboxes = None
            if hasattr(self, '_secondary_keys') and hasattr(self, '_p2'):
                curve_viewboxes = {k: self._p2 for k in self._secondary_keys if k in curve_dict}
            trace_key, x, y = snap_to_nearest(self._plot_widget, curve_dict, ev.scenePos(),
                                              curve_viewboxes=curve_viewboxes)
            if trace_key is not None:
                # Get the series color for the marker
                _, color_hex = self._series_curves.get(trace_key, (None, '#ffffff'))
                self._marker_store.add_marker(trace_key, x, y, color=color_hex)
                
    def _refresh_markers(self):
        plot_item = self._plot_widget.getPlotItem()
        # Remove glyphs from whichever ViewBox they were added to
        for m_id, glyph in self._marker_glyphs.items():
            owner = getattr(glyph, '_owner_vb', None)
            if owner is not None:
                owner.removeItem(glyph)
            else:
                plot_item.removeItem(glyph)
        self._marker_glyphs.clear()

        secondary_keys = getattr(self, '_secondary_keys', set())
        has_p2 = hasattr(self, '_p2')

        # Block signals to avoid infinite recursion (we're called from markers_changed)
        self._marker_store.blockSignals(True)
        for m in self._marker_store.get_markers():
            if m.trace_key in self._series_curves:
                _, new_y = self._get_snapped_position(m, m.x)
                if new_y != m.y:
                    self._marker_store.update_marker(m.id, y=new_y)

            glyph = MarkerGlyph(m)
            glyph.signaler.marker_moved.connect(self._on_marker_dragged)
            glyph.signaler.marker_moving.connect(self._on_marker_moving)
            # Add glyph to the correct ViewBox
            if has_p2 and m.trace_key in secondary_keys:
                self._p2.addItem(glyph)
                glyph._owner_vb = self._p2
            else:
                plot_item.addItem(glyph)
                glyph._owner_vb = None
            self._marker_glyphs[m.id] = glyph
        self._marker_store.blockSignals(False)

        self._marker_overlay.update_markers(self._marker_store)

    def _get_snapped_position(self, m, raw_x: float) -> tuple[float, float]:
        """Calculate the snapped position (x, y) for a given marker and raw x coordinate."""
        if m.trace_key in self._series_curves:
            curve, _ = self._series_curves[m.trace_key]
            x_data, y_data = curve.getData()
            if x_data is not None and len(x_data) > 0:
                # Handle both increasing and decreasing x (FFT might have reversed ranges or weirdness)
                if len(x_data) > 1 and x_data[-1] > x_data[0]:
                    snapped_y = float(np.interp(raw_x, x_data, y_data))
                    snapped_x = float(np.clip(raw_x, x_data[0], x_data[-1]))
                elif len(x_data) > 1 and x_data[0] > x_data[-1]:
                    snapped_y = float(np.interp(raw_x, x_data[::-1], y_data[::-1]))
                    snapped_x = float(np.clip(raw_x, x_data[-1], x_data[0]))
                else:
                    idx = np.argmin(np.abs(x_data - raw_x))
                    snapped_x = float(x_data[idx])
                    snapped_y = float(y_data[idx])
                return snapped_x, snapped_y
        return raw_x, 0.0

    def _on_marker_moving(self, marker_id: str, new_x: float, new_y: float):
        """Handle live visual updates during drag (continuous snapping) with throttling."""
        now = time.perf_counter()
        if hasattr(self, '_last_snap_time') and now - self._last_snap_time < 0.016:  # ~60fps throttle
            return
        self._last_snap_time = now

        m = self._marker_store.get_marker(marker_id)
        if m is None:
            return
        
        # Snap to curve at the new x
        snapped_x, snapped_y = self._get_snapped_position(m, new_x)
        
        # Update visual position
        m.x = snapped_x
        m.y = snapped_y
        if marker_id in self._marker_glyphs:
            self._marker_glyphs[marker_id].set_visual_pos(snapped_x, snapped_y)
        
        # Update overlay text
        self._marker_overlay.update_markers(self._marker_store)

    def _on_marker_dragged(self, marker_id: str, new_x: float, new_y: float):
        """Handle marker drag — snap to nearest series curve point at the dragged x."""
        m = self._marker_store.get_marker(marker_id)
        if m is None:
            return
        
        snapped_x, snapped_y = self._get_snapped_position(m, new_x)
        self._marker_store.update_marker(marker_id, x=snapped_x, y=snapped_y)

    # ── get_plot_data for testing ────────────────────────

    def get_plot_data(self) -> list:
        """Return data currently plotted, for test verification."""
        result = []
        for key, (curve, _color) in self._series_curves.items():
            x_data, y_data = curve.getData()
            if x_data is not None and y_data is not None:
                result.append({'name': key, 'x': list(x_data), 'y': list(y_data)})
            else:
                result.append({'name': key, 'x': [], 'y': []})
        return result


class ComplexRIWidget(ComplexWidget):
    """Real & Imaginary components."""
    
    def __init__(self, var_name: str, color: QColor, parent: Optional[QWidget] = None, trace_id: str = ""):
        super().__init__(var_name, color, parent)
        self._real_curve = self._plot_widget.plot(pen=pg.mkPen('#00ffff', width=1.5), name="Real")
        self._imag_curve = self._plot_widget.plot(pen=pg.mkPen('#ff00ff', width=1.5), name="Imag")
        self._plot_widget.setLabel('left', 'Amplitude')
        
        prefix = f"{trace_id}: {var_name} " if trace_id else ""
        self._legend.addItem(self._real_curve, f"{prefix}(real)")
        self._legend.addItem(self._imag_curve, f"{prefix}(imag)")
        
        self._register_series('Real', self._real_curve, '#00ffff')
        self._register_series('Imag', self._imag_curve, '#ff00ff')

    def update_data(self, value: np.ndarray):
        value = np.atleast_1d(value)
        self._raw_data = value

        self._updating_curves = True
        real = value.real
        imag = value.imag
        x_r, y_r = downsample(real)
        x_i, y_i = downsample(imag)
        self._real_curve.setData(self._get_x_for_indices(x_r), y_r)
        self._imag_curve.setData(self._get_x_for_indices(x_i), y_i)
        self._updating_curves = False

        if self._t_vector is not None:
            self._plot_widget.setLabel('bottom', 'Time')
        self.update_info(f"{value.shape}")
        self._refresh_markers()

    def _render_slice(self, i_min: int, i_max: int):
        """Re-render real & imag for the visible slice."""
        sliced = self._raw_data[i_min:i_max]
        real = sliced.real
        imag = sliced.imag
        x_r, y_r = downsample(real, x_offset=i_min)
        x_i, y_i = downsample(imag, x_offset=i_min)
        self._real_curve.setData(self._get_x_for_indices(x_r), y_r)
        self._imag_curve.setData(self._get_x_for_indices(x_i), y_i)


class ComplexMAWidget(ComplexWidget):
    """Magnitude (Log) & Phase."""
    
    def __init__(self, var_name: str, color: QColor, parent: Optional[QWidget] = None, trace_id: str = ""):
        super().__init__(var_name, color, parent)
        
        # Mag on left axis
        self._mag_curve = self._plot_widget.plot(pen=pg.mkPen('#ffff00', width=1.5), name="Log Mag (dB)")
        self._plot_widget.setLabel('left', 'Magnitude (dB)', color='#ffff00')
        
        self._p1 = self._plot_widget.plotItem
        self._p2 = pg.ViewBox()
        self._p1.showAxis('right')
        self._p1.scene().addItem(self._p2)
        self._p1.getAxis('right').linkToView(self._p2)
        self._p2.setXLink(self._p1)
        self._p1.getAxis('right').setLabel('Phase (rad)', color='#00ff00')
        self._p1.getAxis('right').setZValue(10)
        
        self._phase_curve = pg.PlotDataItem(pen=pg.mkPen('#00ff7f', width=1.5))
        self._p2.addItem(self._phase_curve)
        
        prefix = f"{trace_id}: {var_name} " if trace_id else ""
        self._legend.addItem(self._mag_curve, f"{prefix}(mag_db)")
        self._legend.addItem(self._phase_curve, f"{prefix}(phase_rad)")
        
        self._register_series('Log Mag', self._mag_curve, '#ffff00')
        self._register_series('Phase', self._phase_curve, '#00ff7f')

        # Keys whose curves live in the secondary ViewBox (_p2)
        self._secondary_keys: set = {'Phase'}

        # Replace right axis with editable one
        self._setup_editable_secondary_axis('#00ff00', 'Phase (rad)')

        # Handle view resize
        self._p1.vb.sigResized.connect(self._update_views)
        self._p1.vb.sigYRangeChanged.connect(self._sync_p2_y)
        self._last_mag_range = None
        self._syncing_y = False

    def _sync_p2_y(self):
        """Synchronize secondary Y axis proportionally when primary is panned/zoomed."""
        if self._syncing_y:
            return
        
        mag_range = self._p1.vb.viewRange()[1]
        
        # If auto-ranging or first run, just update baseline and exit
        if self._last_mag_range is None or not self._axis_controller or not self._axis_controller.y_pinned:
            self._last_mag_range = mag_range
            return
            
        self._syncing_y = True
        try:
            mag_h = self._last_mag_range[1] - self._last_mag_range[0]
            if mag_h != 0:
                phase_range = self._p2.viewRange()[1]
                phase_h = phase_range[1] - phase_range[0]
                
                # Proportional shift
                dy_mag = mag_range[0] - self._last_mag_range[0]
                dy_phase = dy_mag * (phase_h / mag_h)
                
                # Proportional zoom
                zoom_ratio = (mag_range[1] - mag_range[0]) / mag_h
                new_phase_h = phase_h * zoom_ratio
                
                new_phase_min = phase_range[0] + dy_phase
                new_phase_max = new_phase_min + new_phase_h
                
                self._p2.setYRange(new_phase_min, new_phase_max, padding=0)
            
            self._last_mag_range = mag_range
        finally:
            self._syncing_y = False

    def _update_views(self):
        self._p2.setGeometry(self._p1.vb.sceneBoundingRect())
        self._p2.linkedViewChanged(self._p1.vb, self._p2.XAxis)

    def _on_pin_state_changed(self, axis: str, is_pinned: bool) -> None:
        """Handle axis pin state - also control secondary Y axis for phase."""
        super()._on_pin_state_changed(axis, is_pinned)
        if axis == 'y':
            self._p2.enableAutoRange(axis='y', enable=not is_pinned)

    def set_series_color(self, series_key: str, color: QColor) -> None:
        """Override to also update axis label colors for dual-axis layout."""
        super().set_series_color(series_key, color)
        hex_color = color.name()
        if series_key == 'Log Mag':
            self._plot_widget.setLabel('left', 'Magnitude (dB)', color=hex_color)
        elif series_key == 'Phase':
            self._p1.getAxis('right').setLabel('Phase (rad)', color=hex_color)

    def update_data(self, value: np.ndarray):
        value = np.atleast_1d(value)
        self._raw_data = value

        self._updating_curves = True
        mag_db = 20 * np.log10(np.abs(value) + 1e-12)
        phase = np.angle(value)
        x_m, y_m = downsample(mag_db)
        x_p, y_p = downsample(phase)
        self._mag_curve.setData(self._get_x_for_indices(x_m), y_m)
        self._phase_curve.setData(self._get_x_for_indices(x_p), y_p)
        self._updating_curves = False

        if self._t_vector is not None:
            self._plot_widget.setLabel('bottom', 'Time')
        self.update_info(f"{value.shape}")
        self._refresh_markers()

    def _render_slice(self, i_min: int, i_max: int):
        """Re-render mag & phase for the visible slice."""
        sliced = self._raw_data[i_min:i_max]
        mag_db = 20 * np.log10(np.abs(sliced) + 1e-12)
        phase = np.angle(sliced)
        x_m, y_m = downsample(mag_db, x_offset=i_min)
        x_p, y_p = downsample(phase, x_offset=i_min)
        self._mag_curve.setData(self._get_x_for_indices(x_m), y_m)
        self._phase_curve.setData(self._get_x_for_indices(x_p), y_p)


class SingleCurveWidget(ComplexWidget):
    """Generic single curve complex view."""
    
    def __init__(self, var_name: str, color: QColor, title: str, parent: Optional[QWidget] = None, trace_id: str = ""):
        super().__init__(var_name, color, parent)
        self._title = title
        self._curve = self._plot_widget.plot(pen=pg.mkPen(color.name(), width=1.5), name=title)
        self._plot_widget.setLabel('left', title)
        
        # M2.5: Ensure legend exists and add primary
        if hasattr(self, '_legend') and self._legend:
            label = f"{trace_id}: {var_name}" if trace_id else title
            self._legend.addItem(self._curve, label)
            
        self._register_series(title, self._curve, color.name())
        self._raw_real_data: Optional[np.ndarray] = None  # Pre-computed real array

    def set_data(self, data: np.ndarray, info: str):
        self._raw_real_data = data
        self._raw_data = data  # Base class zoom guard checks this
        self._updating_curves = True
        x, y = downsample(data)
        self._curve.setData(self._get_x_for_indices(x), y)
        self._updating_curves = False

        if self._t_vector is not None:
            self._plot_widget.setLabel('bottom', 'Time')
        self.update_info(info)
        self._refresh_markers()

    def _render_slice(self, i_min: int, i_max: int):
        """Re-render for the visible slice using pre-computed real data."""
        source = self._raw_real_data if self._raw_real_data is not None else self._raw_data
        if source is None:
            return
        sliced = source[i_min:i_max]
        x, y = downsample(sliced, x_offset=i_min)
        self._curve.setData(self._get_x_for_indices(x), y)

# --- PLUGINS ---

def _extract_complex_waveform(value: Any, dtype: str):
    """Extract (samples, t_vector) from a waveform dict or raw complex array.
    
    Returns:
        (complex_samples, t_vector_or_None)
    """
    # Serialized waveform from IPC
    if isinstance(value, dict) and value.get('__dtype__') == DTYPE_WAVEFORM_COMPLEX:
        samples = np.asarray(value['samples'])
        scalars = value.get('scalars', [0.0, 1.0])
        x0, dx = scalars[0], scalars[1]
        t_vector = x0 + np.arange(len(samples)) * dx
        return samples, t_vector
    
    # Direct waveform object (not serialized)
    if dtype == DTYPE_WAVEFORM_COMPLEX:
        waveform_info = get_waveform_info(value)
        if waveform_info is not None:
            samples = np.asarray(getattr(value, waveform_info['samples_attr']))
            scalar_attrs = waveform_info['scalar_attrs']
            x0 = float(getattr(value, scalar_attrs[0]))
            dx = float(getattr(value, scalar_attrs[1]))
            t_vector = x0 + np.arange(len(samples)) * dx
            return samples, t_vector
    
    # Plain complex array — no t_vector
    return np.asanyarray(value), None


class ComplexRIPlugin(ProbePlugin):
    name = "Real & Imag"
    icon = "activity"
    priority = 90
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype in (DTYPE_ARRAY_COMPLEX, DTYPE_WAVEFORM_COMPLEX)
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None, trace_id: str = "") -> QWidget:
        return ComplexRIWidget(var_name, color, parent, trace_id=trace_id)
    
    def update(self, widget: QWidget, value: Any, dtype: str, shape=None, source_info: str = "") -> None:
        if isinstance(widget, ComplexRIWidget):
            samples, t_vector = _extract_complex_waveform(value, dtype)
            widget._t_vector = t_vector
            widget.update_data(samples)

class ComplexMAPlugin(ProbePlugin):
    name = "Mag & Phase"
    icon = "bar-chart-2"
    priority = 85
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype in (DTYPE_ARRAY_COMPLEX, DTYPE_WAVEFORM_COMPLEX)
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None, trace_id: str = "") -> QWidget:
        return ComplexMAWidget(var_name, color, parent, trace_id=trace_id)
    
    def update(self, widget: QWidget, value: Any, dtype: str, shape=None, source_info: str = "") -> None:
        if isinstance(widget, ComplexMAWidget):
            samples, t_vector = _extract_complex_waveform(value, dtype)
            widget._t_vector = t_vector
            widget.update_data(samples)

class LogMagPlugin(ProbePlugin):
    name = "Log Mag (dB)"
    icon = "activity"
    priority = 80
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype in (DTYPE_ARRAY_COMPLEX, DTYPE_WAVEFORM_COMPLEX)
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None, trace_id: str = "") -> QWidget:
        return SingleCurveWidget(var_name, color, "Magnitude (dB)", parent, trace_id=trace_id)
    
    def update(self, widget: QWidget, value: Any, dtype: str, shape=None, source_info: str = "") -> None:
        if isinstance(widget, SingleCurveWidget):
            samples, t_vector = _extract_complex_waveform(value, dtype)
            widget._t_vector = t_vector
            mag_db = 20 * np.log10(np.abs(samples) + 1e-12)
            widget.set_data(mag_db, f"[{samples.shape}]")

class LinearMagPlugin(ProbePlugin):
    name = "Linear Mag"
    icon = "activity"
    priority = 75
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype in (DTYPE_ARRAY_COMPLEX, DTYPE_WAVEFORM_COMPLEX)
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None, trace_id: str = "") -> QWidget:
        return SingleCurveWidget(var_name, color, "Magnitude", parent, trace_id=trace_id)
    
    def update(self, widget: QWidget, value: Any, dtype: str, shape=None, source_info: str = "") -> None:
        if isinstance(widget, SingleCurveWidget):
            samples, t_vector = _extract_complex_waveform(value, dtype)
            widget._t_vector = t_vector
            widget.set_data(np.abs(samples), f"[{samples.shape}]")

class PhaseRadPlugin(ProbePlugin):
    name = "Phase (rad)"
    icon = "activity"
    priority = 70
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype in (DTYPE_ARRAY_COMPLEX, DTYPE_WAVEFORM_COMPLEX)
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None, trace_id: str = "") -> QWidget:
        return SingleCurveWidget(var_name, color, "Phase (rad)", parent, trace_id=trace_id)
    
    def update(self, widget: QWidget, value: Any, dtype: str, shape=None, source_info: str = "") -> None:
        if isinstance(widget, SingleCurveWidget):
            samples, t_vector = _extract_complex_waveform(value, dtype)
            widget._t_vector = t_vector
            widget.set_data(np.angle(samples), f"[{samples.shape}]")

class PhaseDegPlugin(ProbePlugin):
    name = "Phase (deg)"
    icon = "activity"
    priority = 65
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype in (DTYPE_ARRAY_COMPLEX, DTYPE_WAVEFORM_COMPLEX)
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None, trace_id: str = "") -> QWidget:
        return SingleCurveWidget(var_name, color, "Phase (deg)", parent, trace_id=trace_id)
    
    def update(self, widget: QWidget, value: Any, dtype: str, shape=None, source_info: str = "") -> None:
        if isinstance(widget, SingleCurveWidget):
            samples, t_vector = _extract_complex_waveform(value, dtype)
            widget._t_vector = t_vector
            deg = np.rad2deg(np.angle(samples))
            widget.set_data(deg, f"[{samples.shape}]")
