"""Waveform visualization plugin for 1D arrays."""
from typing import Any, Optional, Tuple, List
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import QRectF, QTimer, Qt, pyqtSignal

from ...plots.pin_layout_mixin import PinLayoutMixin
from ...plots.draw_mode import DrawMode, apply_draw_mode

from ..base import ProbePlugin
from ...core.data_classifier import (
    DTYPE_ARRAY_1D, DTYPE_ARRAY_2D, DTYPE_ARRAY_COMPLEX,
    DTYPE_WAVEFORM_REAL, DTYPE_WAVEFORM_COLLECTION, DTYPE_ARRAY_COLLECTION,
    get_waveform_info, get_waveform_collection_info
)
from ...plots.axis_controller import AxisController
from ...plots.pin_indicator import PinIndicator
from ...plots.editable_axis import EditableAxisItem
from ...gui.axis_editor import AxisEditor
from ...plots.marker_model import MarkerStore
from ...plots.marker_items import MarkerOverlay, MarkerGlyph, snap_to_nearest

# Default color palette (overridden at runtime by theme.row_colors)
ROW_COLORS = [
    '#00ffff',  # 0: Cyan
    '#ff00ff',  # 1: Magenta
    '#ffff00',  # 2: Yellow
    '#00ff7f',  # 3: Green
    '#ff7f00',  # 4: Orange
    '#ff7fff',  # 5: Pink
    '#7fff00',  # 6: Lime
    '#00bfff',  # 7: Sky Blue
    '#ff6b6b',  # 8: Coral
    '#bf7fff',  # 9: Violet
]


class WaveformWidget(PinLayoutMixin, QWidget):
    """The actual plot widget created by WaveformPlugin."""

    status_message_requested = pyqtSignal(str)
    
    MAX_DISPLAY_POINTS = 5000
    
    def __init__(self, var_name: str, color: QColor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._var_name = var_name
        self._color = color
        self._data: Optional[np.ndarray] = None
        self._t_vector: Optional[np.ndarray] = None
        self._curves: List[pg.PlotDataItem] = []
        self._row_visible: List[bool] = []
        self._legend: Optional[pg.LegendItem] = None
        
        # M2.5: Axis controller and pin indicator
        self._axis_controller: Optional[AxisController] = None
        self._pin_indicator: Optional[PinIndicator] = None
        self._axis_editor: Optional[AxisEditor] = None
        
        # Per-curve draw mode: curve_index -> DrawMode
        self._draw_modes: dict = {}  # int -> DrawMode
        self._row_colors = list(ROW_COLORS)

        self._setup_ui()

        from ...gui.theme.theme_manager import ThemeManager
        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.current)
    
    def _setup_ui(self):
        """Create the plot widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Header with variable name
        header = QHBoxLayout()
        self._name_label = QLabel(self._var_name)
        self._name_label.setFont(QFont("JetBrains Mono", 11, QFont.Weight.Bold))
        self._name_label.setStyleSheet(f"color: {self._color.name()};")
        header.addWidget(self._name_label)
        header.addStretch()
        self._info_label = QLabel("")
        self._info_label.setFont(QFont("JetBrains Mono", 9))
        header.addWidget(self._info_label)
        layout.addLayout(header)

        # PyQtGraph plot
        self._plot_widget = pg.PlotWidget()
        self._configure_plot()
        layout.addWidget(self._plot_widget)

        # Stats bar
        self._stats_label = QLabel("Min: -- | Max: -- | Mean: --")
        self._stats_label.setFont(QFont("JetBrains Mono", 9))
        self._stats_label.setStyleSheet(f"color: {self._color.name()};")
        layout.addWidget(self._stats_label)
    
    def _configure_plot(self):
        """Configure plot appearance using probe color."""
        self._plot_widget.setBackground('#0d0d0d')
        # Use a more visible default grid alpha (0.6) before theme override
        self._plot_widget.showGrid(x=True, y=True, alpha=0.6)
        self._plot_widget.useOpenGL(False)
        self._plot_widget.setLabel('left', 'Amplitude')
        self._plot_widget.setLabel('bottom', 'Sample Index')

        axis_pen = pg.mkPen(color=self._color.name(), width=1)
        self._plot_widget.getAxis('left').setPen(axis_pen)
        self._plot_widget.getAxis('bottom').setPen(axis_pen)
        self._plot_widget.getAxis('left').setTextPen(axis_pen)
        self._plot_widget.getAxis('bottom').setTextPen(axis_pen)

        self._curves = [self._plot_widget.plot(
            pen=pg.mkPen(color=self._color.name(), width=1.5),
            antialias=False
        )]
        self._row_visible = [True]
        self._draw_modes[0] = DrawMode.LINE
        
        self._plot_widget.setMouseEnabled(x=True, y=True)
        
        # M2.5: Setup axis controller and pin indicator
        plot_item = self._plot_widget.getPlotItem()
        
        # Zoom-responsive downsampling: re-render when view range changes
        self._zoom_timer = QTimer()
        self._zoom_timer.setSingleShot(True)
        self._zoom_timer.setInterval(50)  # 50ms debounce
        self._zoom_timer.timeout.connect(self._rerender_for_zoom)
        self._updating_curves = False  # Guard against recursion
        vb = plot_item.getViewBox()
        vb.sigRangeChanged.connect(self._on_view_range_changed)
        self._axis_controller = AxisController(plot_item)
        self._axis_controller.pin_state_changed.connect(self._on_pin_state_changed)
        
        self._pin_indicator = PinIndicator(self)  # Parent to WaveformWidget
        self._pin_indicator.x_pin_clicked.connect(lambda: self._axis_controller.toggle_pin('x'))
        self._pin_indicator.y_pin_clicked.connect(lambda: self._axis_controller.toggle_pin('y'))
        self._pin_indicator.raise_()
        self._pin_indicator.show()
        
        # M2.5: Setup editable axes
        self._setup_editable_axes()
        
        # Mouse hover coordinate display
        self._plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)

        # M2.5: Axis editor (inline text editor)
        self._axis_editor = AxisEditor(self._plot_widget)
        self._axis_editor.value_committed.connect(self._on_axis_value_committed)
        self._axis_editor.editing_cancelled.connect(self._on_axis_edit_cancelled)
        
        # M3: Marker System
        self._marker_store = MarkerStore(self)
        self._marker_overlay = MarkerOverlay(self._plot_widget)
        self._marker_store.markers_changed.connect(self._refresh_markers)
        self._marker_overlay.marker_removed_requested.connect(self._marker_store.remove_marker)
        self._marker_glyphs = {}
        
        self._plot_widget.scene().sigMouseClicked.connect(self._on_mouse_clicked)

    
    def _on_pin_state_changed(self, axis: str, is_pinned: bool) -> None:
        """Handle axis pin state change from AxisController."""
        if self._pin_indicator:
            self._pin_indicator.update_state(axis, is_pinned)
    
    @property
    def axis_controller(self) -> Optional[AxisController]:
        """Access the axis controller for external use (e.g., keyboard shortcuts)."""
        return self._axis_controller
    
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

        # Explicitly set grid on current editable axes to prevent PyqtGraph 
        # UI state caching from ignoring the grid update.
        bottom_axis.setGrid(153) # ~0.6 alpha
        left_axis.setGrid(153)

        # Connect edit signals
        bottom_axis.edit_min_requested.connect(lambda val: self._start_axis_edit('x', 'min', val))
        bottom_axis.edit_max_requested.connect(lambda val: self._start_axis_edit('x', 'max', val))
        left_axis.edit_min_requested.connect(lambda val: self._start_axis_edit('y', 'min', val))
        left_axis.edit_max_requested.connect(lambda val: self._start_axis_edit('y', 'max', val))

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

    def _on_axis_edit_cancelled(self) -> None:
        """Handle axis editor cancelled. Nothing to do."""
        pass

    def _apply_theme(self, theme) -> None:
        c = theme.colors
        pc = theme.plot_colors
        grid_alpha = float(pc.get('grid_alpha', 0.28))
        self._row_colors = list(theme.row_colors)
        self._info_label.setStyleSheet(f"color: {c['text_secondary']};")
        self._plot_widget.setBackground(pc['bg'])
        self._plot_widget.showGrid(x=True, y=True, alpha=grid_alpha)
        
        # Manually force the grid alpha on the axes since we replaced them
        # and cached UI state in PlotItem may drop the showGrid update
        alpha_int = int(min(255, max(0, grid_alpha * 255)))
        
        axis_pen = pg.mkPen(color=pc['axis'], width=1)
        for ax_name in ('left', 'bottom'):
            ax = self._plot_widget.getAxis(ax_name)
            ax.setPen(axis_pen)
            ax.setTextPen(axis_pen)
            # hasattr guard in case axis handles grid differently
            if hasattr(ax, 'setGrid'):
                ax.setGrid(alpha_int)

    def _get_row_color(self, row_index: int) -> str:
        """Get deterministic color for row index (cycles through palette)."""
        palette = self._row_colors
        return palette[row_index % len(palette)]

    def set_color(self, color: QColor) -> None:
        """Update the primary probe color (name label, stats, axes, primary curve)."""
        self._color = color
        hex_color = color.name()
        self._name_label.setStyleSheet(f"color: {hex_color};")
        self._stats_label.setStyleSheet(f"color: {hex_color};")
        axis_pen = pg.mkPen(color=hex_color, width=1)
        for ax_name in ('left', 'bottom'):
            ax = self._plot_widget.getAxis(ax_name)
            if ax is not None:
                ax.setPen(axis_pen)
                ax.setTextPen(axis_pen)
        # Update primary curve if single-curve mode
        if len(self._curves) == 1:
            self._curves[0].setPen(pg.mkPen(hex_color, width=1.5))
            mode = self._draw_modes.get(0, DrawMode.LINE)
            apply_draw_mode(self._curves[0], mode, hex_color)

    def set_series_color(self, series_key: int, color: QColor) -> None:
        """Change the color of a curve by index."""
        if series_key < 0 or series_key >= len(self._curves):
            return
        hex_color = color.name()
        self._curves[series_key].setPen(pg.mkPen(hex_color, width=1.5))
        mode = self._draw_modes.get(series_key, DrawMode.LINE)
        apply_draw_mode(self._curves[series_key], mode, hex_color)

    def _ensure_curves(self, num_rows: int):
        """Ensure we have the right number of curve objects."""
        current_count = len(self._curves)
        
        if num_rows == current_count:
            return
        
        # Remove legend if exists (will recreate)
        if self._legend is not None:
            self._legend.scene().removeItem(self._legend)
            self._legend = None
        
        # Add more curves if needed
        while len(self._curves) < num_rows:
            idx = len(self._curves)
            # Row 0 uses probe color, others use palette
            # OR: just use palette for all if > 1 to ensure distinctness?
            # Decision: use palette for all only if num_rows > 1 is anticipated OR just strict palette.
            # But the first curve is already created with probe color.
            # Let's keep curve 0 as probe color, and subsequent as palette?
            # Might be confusing. Let's strictly use palette for indices > 0.
            color = self._get_row_color(idx)
            curve = self._plot_widget.plot(
                pen=pg.mkPen(color=color, width=1.5),
                antialias=False,
                name=f"Row {idx}"
            )
            self._curves.append(curve)
            self._row_visible.append(True)
            self._draw_modes[idx] = DrawMode.LINE
        
        # Remove excess curves if needed
        while len(self._curves) > num_rows:
            removed_idx = len(self._curves) - 1
            curve = self._curves.pop()
            self._row_visible.pop()
            self._draw_modes.pop(removed_idx, None)
            self._plot_widget.removeItem(curve)
        
        # Create legend for multi-row (>1 row)
        if num_rows > 1:
            from ...gui.theme.theme_manager import ThemeManager
            tc = ThemeManager.instance().current.colors
            self._legend = self._plot_widget.addLegend(
                offset=(10, 10),
                labelTextColor=tc['text_primary'],
                brush=pg.mkBrush(tc['bg_medium'] + '80')
            )
            for idx, curve in enumerate(self._curves):
                self._legend.addItem(curve, f"Row {idx}")
            
            # Connect legend click for visibility toggle
            for idx, item in enumerate(self._legend.items):
                label = item[1]
                label.setAttr('idx', idx)
                label.mousePressEvent = lambda ev, i=idx: self._toggle_row(i)

    def _toggle_row(self, row_index: int):
        """Toggle visibility of a row."""
        if row_index < len(self._curves):
            self._row_visible[row_index] = not self._row_visible[row_index]
            self._curves[row_index].setVisible(self._row_visible[row_index])

    def downsample(self, data: np.ndarray, n_points: int = 0, x_offset: int = 0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Downsample data for display while preserving visual features.
        Uses min-max decimation to preserve peaks.
        
        Args:
            data: The array to downsample.
            n_points: Max display points (0 = use MAX_DISPLAY_POINTS).
            x_offset: Offset added to x-indices (for sliced data).
        
        Returns:
            (x_indices, y_values) tuple. x_indices map back to original
            sample positions so the plot x-axis stays correct.
        """
        if n_points <= 0:
            n_points = self.MAX_DISPLAY_POINTS
        
        if len(data) <= n_points:
            return np.arange(len(data)) + x_offset, data

        # Number of chunks
        n_chunks = n_points // 2
        chunk_size = len(data) // n_chunks

        # Reshape and get min/max per chunk
        # Truncate to multiple of chunk_size
        truncated = data[:n_chunks * chunk_size]
        reshaped = truncated.reshape(n_chunks, chunk_size)

        mins = reshaped.min(axis=1)
        maxs = reshaped.max(axis=1)

        # Build x-indices that map back to original sample positions
        chunk_starts = np.arange(n_chunks) * chunk_size
        x = np.empty(n_chunks * 2, dtype=np.int64)
        x[0::2] = chunk_starts + x_offset
        x[1::2] = chunk_starts + (chunk_size - 1) + x_offset

        # Interleave min and max y-values
        y = np.empty(n_chunks * 2, dtype=data.dtype)
        y[0::2] = mins
        y[1::2] = maxs

        return x, y

    def update_data(self, value: Any, dtype: str, shape: Optional[Tuple[int, ...]] = None, source_info: str = "") -> None:
        """Update the widget with new data."""
        if value is None:
            return

        # Handle serialized waveform collection from IPC
        if isinstance(value, dict) and value.get('__dtype__') == DTYPE_WAVEFORM_COLLECTION:
            self._update_waveform_collection_data(value, dtype, shape, source_info)
            return

        # Handle serialized array collection from IPC
        if isinstance(value, dict) and value.get('__dtype__') == DTYPE_ARRAY_COLLECTION:
            self._update_array_collection_data(value, dtype, shape, source_info)
            return

        # Handle waveform objects (2 scalars + 1 array)
        t_vector = None
        
        # Serialized single waveform from IPC
        if isinstance(value, dict) and value.get('__dtype__') == DTYPE_WAVEFORM_REAL:
            samples = np.asarray(value['samples'])
            scalars = value.get('scalars', [0.0, 1.0])  # [t0, dt] sorted
            t0, dt = scalars[0], scalars[1]
            t_vector = t0 + np.arange(len(samples)) * dt
            value = samples
        else:
            # Check for direct waveform collection object
            collection_info = get_waveform_collection_info(value)
            if collection_info is not None:
                # Convert to serialized format and handle
                serialized = {
                    '__dtype__': DTYPE_WAVEFORM_COLLECTION,
                    'waveforms': []
                }
                for wf_data in collection_info['waveforms']:
                    obj = wf_data['obj']
                    info = wf_data['info']
                    samples = np.asarray(getattr(obj, info['samples_attr']))
                    scalars = [float(getattr(obj, attr)) for attr in info['scalar_attrs']]
                    serialized['waveforms'].append({'samples': samples, 'scalars': scalars})
                self._update_waveform_collection_data(serialized, dtype, shape, source_info)
                return

            # Check for direct single waveform object
            waveform_info = get_waveform_info(value)
            if waveform_info is not None:
                samples_attr = waveform_info['samples_attr']
                scalar_attrs = waveform_info['scalar_attrs']
                samples = np.asarray(getattr(value, samples_attr))
                scalars = [float(getattr(value, attr)) for attr in scalar_attrs]
                t0, dt = scalars[0], scalars[1]
                t_vector = t0 + np.arange(len(samples)) * dt
                value = samples

        # Convert to numpy array if needed
        if not isinstance(value, np.ndarray):
            try:
                value = np.asarray(value)
            except (ValueError, TypeError):
                return
        
        # Ensure at least 1D
        if value.ndim == 0:
            value = np.atleast_1d(value)
        
        # Handle complex data: take absolute value (magnitude)
        if np.iscomplexobj(value) or dtype == DTYPE_ARRAY_COMPLEX:
            value = np.abs(value)
            source_info = f"{source_info} (magnitude)"

        self._t_vector = t_vector

        # Handle 2D arrays: each row is a separate time series
        if value.ndim == 2:
            self._update_2d_data(value, dtype, shape, source_info)
        else:
            self._update_1d_data(value, dtype, shape, source_info)

    def _update_1d_data(self, value: np.ndarray, dtype: str, shape: Optional[tuple], source_info: str):
        """Update plot with 1D data."""
        self._data = value.flatten() if value.ndim > 1 else value
        
        # Ensure single curve
        self._ensure_curves(1)
        self._curves[0].setPen(pg.mkPen(color=self._color.name(), width=1.5)) # Ensure probe color
        # Re-apply draw mode in case it was reset by _ensure_curves
        mode = self._draw_modes.get(0, DrawMode.LINE)
        apply_draw_mode(self._curves[0], mode, self._color.name())

        # Downsample if needed
        x_display, y_display = self.downsample(self._data)

        # Update plot - use time vector if available (Waveform objects)
        self._updating_curves = True
        if self._t_vector is not None and len(self._t_vector) == len(self._data):
            # Map sample indices through time vector
            t_display = self._t_vector[x_display]
            self._curves[0].setData(t_display, y_display)
            self._plot_widget.setLabel('bottom', 'Time')
        else:
            self._curves[0].setData(x_display, y_display)
            self._plot_widget.setLabel('bottom', 'Sample Index')
        self._updating_curves = False

        # Update info label
        self._info_label.setText(source_info)

        # Update stats
        self._update_stats_from_data(self._data, shape=shape if shape else value.shape)

        self._refresh_markers()


    def _update_2d_data(self, value: np.ndarray, dtype: str, shape: Optional[tuple], source_info: str):
        """Update plot with 2D data (each row is a time series)."""
        num_rows = value.shape[0]
        self._data = value  # Store full 2D array
        
        # Ensure correct number of curves
        self._ensure_curves(num_rows)

        # Update each row
        self._updating_curves = True
        for row_idx in range(num_rows):
            row_data = value[row_idx, :]
            x_display, y_display = self.downsample(row_data)
            
            if self._t_vector is not None and len(self._t_vector) == len(row_data):
                t_display = self._t_vector[x_display]
                self._curves[row_idx].setData(t_display, y_display)
            else:
                self._curves[row_idx].setData(x_display, y_display)
        self._updating_curves = False

        # Set x-axis label
        if self._t_vector is not None:
            self._plot_widget.setLabel('bottom', 'Time')
        else:
            self._plot_widget.setLabel('bottom', 'Sample Index')

        # Update info label
        self._info_label.setText(source_info)

        # Update stats (aggregate across all rows)
        self._update_stats_from_data(self._data, prefix=f"{value.shape[0]} rows", shape=shape if shape else value.shape)

        self._refresh_markers()


    def _update_waveform_collection_data(self, value: dict, dtype: str, shape: Optional[tuple], source_info: str):
        """Update plot with waveform collection."""
        waveforms = value.get('waveforms', [])
        num_waveforms = len(waveforms)
        
        if num_waveforms == 0:
            return
        
        # Ensure correct number of curves
        self._ensure_curves(num_waveforms)

        # Collect all samples for stats
        all_samples = []

        # Update each waveform with its own time vector
        self._updating_curves = True
        for idx, wf in enumerate(waveforms):
            samples = np.asarray(wf['samples'])
            scalars = wf.get('scalars', [0.0, 1.0])
            t0, dt = scalars[0], scalars[1]
            
            # Compute time vector for this specific waveform
            t_vector = t0 + np.arange(len(samples)) * dt
            
            x_indices, y_display = self.downsample(samples)
            # Map sample indices through time vector
            t_display = t_vector[x_indices]
            
            self._curves[idx].setData(t_display, y_display)
            all_samples.append(samples)
        self._updating_curves = False

        self._plot_widget.setLabel('bottom', 'Time')
        self._info_label.setText(source_info)

        if all_samples:
            all_data = np.concatenate(all_samples)
            self._update_stats_from_data(all_data, f"{num_waveforms} wfms", shape=(num_waveforms, len(all_samples[0])) if all_samples else None)
        
        self._refresh_markers()

    def _update_array_collection_data(self, value: dict, dtype: str, shape: Optional[tuple], source_info: str):
        """Update plot with array collection."""
        arrays = value.get('arrays', [])
        num_arrays = len(arrays)
        
        if num_arrays == 0:
            return
        
        self._ensure_curves(num_arrays)
        all_data = []

        self._updating_curves = True
        for idx, arr in enumerate(arrays):
            samples = np.asarray(arr)
            x_display, y_display = self.downsample(samples)
            self._curves[idx].setData(x_display, y_display)
            all_data.append(samples)
        self._updating_curves = False

        self._plot_widget.setLabel('bottom', 'Sample Index')
        self._info_label.setText(source_info)

        if all_data:
            concatenated = np.concatenate(all_data)
            self._update_stats_from_data(concatenated, f"{num_arrays} arrays", shape=(num_arrays, len(all_data[0])) if all_data else None)
            
        self._refresh_markers()

    def _update_stats(self):
        """Update statistics display for 1D data."""
        if self._data is None or len(self._data) == 0:
            return
        self._update_stats_from_data(self._data)

    def _update_stats_2d(self):
        """Update statistics display for 2D data (aggregate)."""
        if self._data is None or self._data.size == 0:
            return
        self._update_stats_from_data(self._data, f"{self._data.shape[0]} rows")

    def _update_stats_from_data(self, data: np.ndarray, prefix: str = "", shape: Optional[tuple] = None):
        min_val = np.min(data)
        max_val = np.max(data)
        mean_val = np.mean(data)
        
        prefix_parts = []
        if shape is not None:
            prefix_parts.append(f"Shape: {shape}")
        if prefix:
            prefix_parts.append(prefix)
            
        prefix_str = " | ".join(prefix_parts) + " | " if prefix_parts else ""
        self._stats_label.setText(
            f"{prefix_str}Min: {min_val:.4g} | Max: {max_val:.4g} | Mean: {mean_val:.4g}"
        )

    def _on_view_range_changed(self, vb, ranges):
        """Handle view range changes — debounce and re-render."""
        if self._updating_curves or self._data is None:
            return
        self._zoom_timer.start()

    def _rerender_for_zoom(self):
        """Re-downsample or show raw data based on visible x-range."""
        if self._data is None:
            return
        
        plot_item = self._plot_widget.getPlotItem()
        vb = plot_item.getViewBox()
        x_min, x_max = vb.viewRange()[0]
        
        def get_indices(n_length):
            if self._t_vector is not None and len(self._t_vector) == n_length:
                if self._t_vector[-1] > self._t_vector[0]:
                    import bisect
                    i_min = bisect.bisect_left(self._t_vector, x_min)
                    i_max = bisect.bisect_right(self._t_vector, x_max)
                    return max(0, i_min), min(n_length, i_max)
            return max(0, int(np.floor(x_min))), min(n_length, int(np.ceil(x_max)) + 1)
            
        # For 1D data
        if self._data.ndim == 1:
            n = len(self._data)
            i_min, i_max = get_indices(n)
            if i_min >= i_max:
                return
            
            visible_slice = self._data[i_min:i_max]
            visible_count = len(visible_slice)
            
            self._updating_curves = True
            if visible_count <= self.MAX_DISPLAY_POINTS:
                # Full resolution for visible slice
                x = np.arange(i_min, i_max)
                y = visible_slice
            else:
                # Re-downsample the visible slice
                x, y = self.downsample(visible_slice, x_offset=i_min)
            
            if self._t_vector is not None and len(self._t_vector) == len(self._data):
                self._curves[0].setData(self._t_vector[x], y)
            else:
                self._curves[0].setData(x, y)
            self._updating_curves = False
        
        elif self._data.ndim == 2:
            # 2D: re-downsample each row for visible range
            n_cols = self._data.shape[1]
            i_min, i_max = get_indices(n_cols)
            if i_min >= i_max:
                return
            
            self._updating_curves = True
            for row_idx in range(min(self._data.shape[0], len(self._curves))):
                row_slice = self._data[row_idx, i_min:i_max]
                if len(row_slice) <= self.MAX_DISPLAY_POINTS:
                    x = np.arange(i_min, i_max)
                    y = row_slice
                else:
                    x, y = self.downsample(row_slice, x_offset=i_min)
                
                if self._t_vector is not None and len(self._t_vector) == n_cols:
                    self._curves[row_idx].setData(self._t_vector[x], y)
                else:
                    self._curves[row_idx].setData(x, y)
            self._updating_curves = False

    def reset_view(self) -> None:
        """Reset the view: restore full data to curves, unpin axes, snap to full range.
        
        _rerender_for_zoom replaces curve data with the visible-range-only slice.
        A bare autoRange() would then fit only to that partial data, causing
        incremental widening instead of a snap. This method restores the full
        dataset before auto-ranging.
        """
        if self._data is None:
            return
        
        # 1. Restore full dataset to curves
        self._updating_curves = True
        if self._data.ndim == 1:
            x_display, y_display = self.downsample(self._data)
            if self._t_vector is not None and len(self._t_vector) == len(self._data):
                self._curves[0].setData(self._t_vector[x_display], y_display)
            else:
                self._curves[0].setData(x_display, y_display)
        elif self._data.ndim == 2:
            for row_idx in range(min(self._data.shape[0], len(self._curves))):
                row_data = self._data[row_idx, :]
                x_display, y_display = self.downsample(row_data)
                if self._t_vector is not None and len(self._t_vector) == self._data.shape[1]:
                    self._curves[row_idx].setData(self._t_vector[x_display], y_display)
                else:
                    self._curves[row_idx].setData(x_display, y_display)
        self._updating_curves = False
        
        # 2. Unpin axes and snap to full range
        if self._axis_controller:
            self._axis_controller.set_pinned('x', False)
            self._axis_controller.set_pinned('y', False)
        
        vb = self._plot_widget.getPlotItem().getViewBox()
        vb.autoRange(padding=0)

    # ── Mouse hover coordinate helpers ─────────────────────

    def _get_active_viewbox(self):
        """Return the viewbox to use for coordinate mapping.

        For dual-axis subclasses, prefer the primary (magnitude) ViewBox.
        Fall back to secondary if magnitude curves are all hidden.
        """
        primary_vb = self._plot_widget.plotItem.vb
        if hasattr(self, '_p2'):
            # Check if primary curves are all hidden
            all_hidden = all(not c.isVisible() for c in self._curves)
            if all_hidden:
                return self._p2
        return primary_vb

    def _on_mouse_moved(self, pos):
        """Format hover coordinates and emit status_message_requested."""
        from .complex_plots import format_coord
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
            curve_dict = {i: c for i, c in enumerate(self._curves)}
            trace_key, x, y = snap_to_nearest(self._plot_widget, curve_dict, ev.scenePos())
            if trace_key is not None:
                self._marker_store.add_marker(trace_key, x, y)
                
    def _refresh_markers(self):
        plot_item = self._plot_widget.getPlotItem()
        for glyph in self._marker_glyphs.values():
            plot_item.removeItem(glyph)
        self._marker_glyphs.clear()
        
        # Block signals to avoid infinite recursion (we're called from markers_changed)
        self._marker_store.blockSignals(True)
        for m in self._marker_store.get_markers():
            # If the curve shifted due to new data, re-evaluate Y
            if isinstance(m.trace_key, int) and m.trace_key < len(self._curves):
                curve = self._curves[m.trace_key]
                x_data, y_data = curve.getData()
                if x_data is not None and len(x_data) > 0:
                    idx = np.argmin(np.abs(x_data - m.x))
                    new_y = float(y_data[idx])
                    if new_y != m.y:
                        self._marker_store.update_marker(m.id, y=new_y)
            
            glyph = MarkerGlyph(m)
            glyph.signaler.marker_moved.connect(self._on_marker_dragged)
            glyph.signaler.marker_moving.connect(self._on_marker_moving)
            plot_item.addItem(glyph)
            self._marker_glyphs[m.id] = glyph
        self._marker_store.blockSignals(False)
            
        self._marker_overlay.update_markers(self._marker_store)

    def _on_marker_moving(self, marker_id: str, new_x: float, new_y: float):
        """Handle live visual updates during drag (continuous snapping) with throttling."""
        import time
        now = time.perf_counter()
        if hasattr(self, '_last_snap_time') and now - self._last_snap_time < 0.016:  # ~60fps throttle
            return
        self._last_snap_time = now

        m = self._marker_store.get_marker(marker_id)
        if m is None:
            return
        
        # Snap to curve at the new x
        if isinstance(m.trace_key, int) and m.trace_key < len(self._curves):
            curve = self._curves[m.trace_key]
            x_data, y_data = curve.getData()
            if x_data is not None and len(x_data) > 0:
                if len(x_data) > 1 and x_data[-1] > x_data[0]:
                    snapped_y = float(np.interp(new_x, x_data, y_data))
                    snapped_x = float(np.clip(new_x, x_data[0], x_data[-1]))
                elif len(x_data) > 1 and x_data[0] > x_data[-1]:
                    snapped_y = float(np.interp(new_x, x_data[::-1], y_data[::-1]))
                    snapped_x = float(np.clip(new_x, x_data[-1], x_data[0]))
                else:
                    idx = np.argmin(np.abs(x_data - new_x))
                    snapped_x = float(x_data[idx])
                    snapped_y = float(y_data[idx])
                
                # Update visual position
                m.x = snapped_x
                m.y = snapped_y
                if marker_id in self._marker_glyphs:
                    self._marker_glyphs[marker_id].set_visual_pos(snapped_x, snapped_y)
                
                # Update overlay text
                self._marker_overlay.update_markers(self._marker_store)

    def _on_marker_dragged(self, marker_id: str, new_x: float, new_y: float):
        """Handle marker drag — snap to nearest curve point at the dragged x."""
        m = self._marker_store.get_marker(marker_id)
        if m is None:
            return
        # Snap to curve at the new x
        if isinstance(m.trace_key, int) and m.trace_key < len(self._curves):
            curve = self._curves[m.trace_key]
            x_data, y_data = curve.getData()
            if x_data is not None and len(x_data) > 0:
                idx = np.argmin(np.abs(x_data - new_x))
                new_x = float(x_data[idx])
                new_y = float(y_data[idx])
        self._marker_store.update_marker(marker_id, x=new_x, y=new_y)
        
    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if hasattr(self, '_marker_overlay'):
            self._marker_overlay._reposition()


    def set_draw_mode(self, curve_index: int, mode: DrawMode) -> None:
        """Set the draw mode for a curve by index."""
        if curve_index < 0 or curve_index >= len(self._curves):
            return
        self._draw_modes[curve_index] = mode
        # Determine color for this curve
        if len(self._curves) == 1:
            color = self._color.name()
        else:
            color = self._get_row_color(curve_index)
        apply_draw_mode(self._curves[curve_index], mode, color)

    def get_draw_mode(self, curve_index: int) -> DrawMode:
        """Get the current draw mode for a curve by index."""
        return self._draw_modes.get(curve_index, DrawMode.LINE)

    @property
    def series_keys(self) -> list:
        """Return the list of curve indices as series keys."""
        return list(range(len(self._curves)))

    def get_plot_data(self) -> list:
        """
        Return the data currently plotted on the graph.
        
        Returns a list of dicts, one per curve (including overlays):
        [{'name': 'signal_i', 'x': [...], 'y': [...], 'is_overlay': False}, ...]
        
        This allows tests to verify what is actually rendered.
        """
        result = []
        for curve in self._curves:
            x_data, y_data = curve.getData()
            if x_data is not None and y_data is not None:
                result.append({
                    'name': self._var_name,
                    'x': list(x_data),
                    'y': list(y_data),
                    'is_overlay': False
                })
            else:
                result.append({'name': self._var_name, 'x': [], 'y': [], 'is_overlay': False})
        
        # Include overlay curves if present
        if hasattr(self, '_overlay_curves'):
            for key, curve in self._overlay_curves.items():
                x_data, y_data = curve.getData()
                if x_data is not None and y_data is not None:
                    result.append({
                        'name': key,
                        'x': list(x_data),
                        'y': list(y_data),
                        'is_overlay': True
                    })
        
        return result


class WaveformFftMagAngleWidget(WaveformWidget):
    """FFT Magnitude (dB) & Angle (deg) with Kaiser Bessel window for 1D arrays."""
    
    def __init__(self, var_name: str, color: QColor, parent: Optional[QWidget] = None):
        super().__init__(var_name, color, parent)
        self._plot_widget.setLabel('bottom', 'Frequency')
        self._plot_widget.setLabel('left', 'Magnitude (dB)')
        self._info_label.setText("FFT Mag (dB) / Angle (deg)")
        self.MAX_DISPLAY_POINTS = 1000000
        self._phase_display_points = 5000
        self._first_data = True
        
        # Calculate a complementary color for the phase axis & curves
        c = QColor(self._color)
        h, s, v, a = c.getHsv()
        c.setHsv((h + 180) % 360, max(150, s), v, a)
        self._phase_color = c.name()
        
        self._p1 = self._plot_widget.plotItem
        self._p2 = pg.ViewBox()
        self._p1.showAxis('right')
        self._p1.scene().addItem(self._p2)
        self._p1.getAxis('right').linkToView(self._p2)
        self._p2.setXLink(self._p1)
        self._p1.getAxis('right').setLabel('Angle (deg)', color=self._phase_color)
        self._p1.getAxis('right').setZValue(10)
        
        # Replace right axis with editable one for double-click editing
        self._setup_editable_secondary_axis(self._phase_color, 'Angle (deg)')
        
        self._legend = self._plot_widget.addLegend(offset=(10, 10))
        self._legend.addItem(self._curves[0], "FFT Mag (dB)")
        self._phase_legend_added = False
        
        self._phase_curves = []
        self._current_phase_data = None
        self._p1.vb.sigResized.connect(self._update_views)
        # FFT angle is naturally bounded to [-180, 180] and doesn't need
        # continuous y auto-ranging on every frame update.
        self._p2.enableAutoRange(axis='y', enable=False)
        self._p2.setYRange(-180.0, 180.0, padding=0)

    def _update_views(self):
        self._p2.setGeometry(self._p1.vb.sceneBoundingRect())
        self._p2.linkedViewChanged(self._p1.vb, self._p2.XAxis)

    def _on_pin_state_changed(self, axis: str, is_pinned: bool) -> None:
        super()._on_pin_state_changed(axis, is_pinned)
        if axis == 'y':
            self._p2.enableAutoRange(axis='y', enable=False)
            if not is_pinned:
                self._p2.setYRange(-180.0, 180.0, padding=0)

    def _setup_editable_secondary_axis(self, secondary_color: str, label: str = '') -> None:
        """Replace the right axis with an EditableAxisItem for double-click editing."""
        from ...plots.editable_axis import EditableAxisItem
        right_axis = EditableAxisItem('right')
        axis_pen = pg.mkPen(color=secondary_color, width=1)
        right_axis.setPen(axis_pen)
        right_axis.setTextPen(axis_pen)
        right_axis.setZValue(10)

        self._p1.setAxisItems({'right': right_axis})
        right_axis.linkToView(self._p2)
        if label:
            right_axis.setLabel(label, color=secondary_color)

        right_axis.edit_min_requested.connect(lambda val: self._start_axis_edit('y2', 'min', val))
        right_axis.edit_max_requested.connect(lambda val: self._start_axis_edit('y2', 'max', val))

    def _start_axis_edit(self, axis: str, endpoint: str, current_value: float) -> None:
        """Start inline editing — extends parent to also handle 'y2' (secondary axis)."""
        if self._axis_editor is None:
            return

        self._axis_editor.setProperty('edit_axis', axis)
        self._axis_editor.setProperty('edit_endpoint', endpoint)

        if axis == 'x':
            x = 40 if endpoint == 'min' else self._plot_widget.width() - 60
            y = self._plot_widget.height() - 20
        elif axis == 'y2':
            x = self._plot_widget.width() - 20
            y = self._plot_widget.height() - 40 if endpoint == 'min' else 20
        else:
            x = 20
            y = self._plot_widget.height() - 40 if endpoint == 'min' else 20

        self._axis_editor.show_at(x, y, current_value)

    def _on_axis_value_committed(self, value: float) -> None:
        """Handle axis editor value — extends parent to also handle 'y2'."""
        axis = self._axis_editor.property('edit_axis')
        endpoint = self._axis_editor.property('edit_endpoint')

        if axis == 'y2' and hasattr(self, '_p2'):
            current_range = self._p2.viewRange()[1]
            if endpoint == 'min':
                self._p2.setYRange(value, current_range[1], padding=0)
            else:
                self._p2.setYRange(current_range[0], value, padding=0)
            if self._axis_controller:
                self._axis_controller.set_pinned('y', True)
        else:
            super()._on_axis_value_committed(value)

    def _ensure_phase_curves(self, num_rows: int):
        while len(self._phase_curves) < num_rows:
            idx = len(self._phase_curves)
            color = self._get_row_color(idx) if num_rows > 1 else self._phase_color
            pen = pg.mkPen(color=color, width=1.2)
            curve = pg.PlotDataItem(pen=pen, antialias=False)
            self._p2.addItem(curve)
            self._phase_curves.append(curve)
            if not self._phase_legend_added:
                self._legend.addItem(curve, "Angle (deg)")
                self._phase_legend_added = True
        while len(self._phase_curves) > num_rows:
            curve = self._phase_curves.pop()
            self._p2.removeItem(curve)

    def _has_visible_phase_curves(self) -> bool:
        return any(curve.isVisible() for curve in self._phase_curves)

    def _render_phase_curves_full(self):
        if self._current_phase_data is None or not self._has_visible_phase_curves():
            return
        self._updating_curves = True
        if self._current_phase_data.ndim == 1:
            x_idx, y_disp = self.downsample(
                self._current_phase_data, n_points=self._phase_display_points
            )
            if self._t_vector is not None and len(self._t_vector) == len(self._current_phase_data):
                self._phase_curves[0].setData(self._t_vector[x_idx], y_disp)
            else:
                self._phase_curves[0].setData(x_idx, y_disp)
        elif self._current_phase_data.ndim == 2:
            n_cols = self._current_phase_data.shape[1]
            for row_idx in range(min(self._current_phase_data.shape[0], len(self._phase_curves))):
                x_idx, y_disp = self.downsample(
                    self._current_phase_data[row_idx], n_points=self._phase_display_points
                )
                if self._t_vector is not None and len(self._t_vector) == n_cols:
                    self._phase_curves[row_idx].setData(self._t_vector[x_idx], y_disp)
                else:
                    self._phase_curves[row_idx].setData(x_idx, y_disp)
        self._updating_curves = False

    def _rerender_for_zoom(self):
        super()._rerender_for_zoom()
        if self._current_phase_data is None or not self._has_visible_phase_curves():
            return
            
        plot_item = self._plot_widget.getPlotItem()
        vb = plot_item.getViewBox()
        x_min, x_max = vb.viewRange()[0]
        
        def get_indices(n_length):
            if self._t_vector is not None and len(self._t_vector) == n_length:
                if self._t_vector[-1] > self._t_vector[0]:
                    import bisect
                    i_min = bisect.bisect_left(self._t_vector, x_min)
                    i_max = bisect.bisect_right(self._t_vector, x_max)
                    return max(0, i_min), min(n_length, i_max)
            return max(0, int(np.floor(x_min))), min(n_length, int(np.ceil(x_max)) + 1)
        
        self._updating_curves = True
        if self._current_phase_data.ndim == 1:
            n = len(self._current_phase_data)
            i_min, i_max = get_indices(n)
            if i_min < i_max:
                slice_data = self._current_phase_data[i_min:i_max]
                if len(slice_data) <= self._phase_display_points:
                    x, y = np.arange(i_min, i_max), slice_data
                else:
                    x, y = self.downsample(
                        slice_data, n_points=self._phase_display_points, x_offset=i_min
                    )
                
                if self._t_vector is not None and len(self._t_vector) == n:
                    self._phase_curves[0].setData(self._t_vector[x], y)
                else:
                    self._phase_curves[0].setData(x, y)
                    
        elif self._current_phase_data.ndim == 2:
            n_cols = self._current_phase_data.shape[1]
            i_min, i_max = get_indices(n_cols)
            if i_min < i_max:
                for row_idx in range(min(self._current_phase_data.shape[0], len(self._phase_curves))):
                    row_slice = self._current_phase_data[row_idx, i_min:i_max]
                    if len(row_slice) <= self._phase_display_points:
                        x, y = np.arange(i_min, i_max), row_slice
                    else:
                        x, y = self.downsample(
                            row_slice, n_points=self._phase_display_points, x_offset=i_min
                        )
                        
                    if self._t_vector is not None and len(self._t_vector) == n_cols:
                        self._phase_curves[row_idx].setData(self._t_vector[x], y)
                    else:
                        self._phase_curves[row_idx].setData(x, y)
        self._updating_curves = False

    def reset_view(self) -> None:
        super().reset_view()
        self._render_phase_curves_full()
        self._p2.setYRange(-180.0, 180.0, padding=0)

    def update_data(self, value: Any, dtype: str, shape: Optional[Tuple[int, ...]] = None, source_info: str = "") -> None:
        if value is None:
            return

        dt = 1.0
        is_waveform = False
        
        if isinstance(value, dict) and value.get('__dtype__') == DTYPE_WAVEFORM_REAL:
            samples = np.asarray(value['samples'])
            scalars = value.get('scalars', [0.0, 1.0])
            dt = scalars[1]
            value = samples
            is_waveform = True
        elif not isinstance(value, (dict, list, np.ndarray)):
            from ...core.data_classifier import get_waveform_info
            info = get_waveform_info(value)
            if info:
                samples = np.asarray(getattr(value, info['samples_attr']))
                scalars = [float(getattr(value, attr)) for attr in info['scalar_attrs']]
                dt = scalars[1]
                value = samples
                is_waveform = True

        if not isinstance(value, np.ndarray) and not isinstance(value, dict):
            try:
                value = np.asarray(value)
            except:
                return
                
        if isinstance(value, np.ndarray):
            if value.ndim == 0:
                value = np.atleast_1d(value)
            
            def compute_fft(data_arr, dt_val):
                n = len(data_arr)
                if n == 0:
                    return data_arr, None, None
                import scipy.signal
                window = scipy.signal.windows.kaiser(n, beta=9)
                windowed = data_arr * window
                nfft = max(8192, 2**int(np.ceil(np.log2(n))))
                fft_data = np.fft.fftshift(np.fft.fft(windowed, n=nfft))
                fft_mag = 20 * np.log10(np.abs(fft_data) + 1e-12) - 20 * np.log10(nfft)
                fft_phase = np.rad2deg(np.angle(fft_data))
                
                if is_waveform and dt_val > 0:
                    freqs = np.fft.fftshift(np.fft.fftfreq(nfft, d=dt_val))
                else:
                    freqs = np.arange(-nfft//2, nfft - nfft//2)
                return fft_mag, fft_phase, freqs

            if value.ndim == 1:
                fft_mag, fft_phase, freqs = compute_fft(value, dt)
                self._t_vector = freqs
                self._current_phase_data = fft_phase
                self._ensure_phase_curves(1)
                super()._update_1d_data(fft_mag, dtype, shape, source_info + " (FFT)")
                self._plot_widget.setLabel('bottom', 'Frequency (Hz)' if is_waveform else 'FFT Bin')
                self._render_phase_curves_full()
                
            elif value.ndim == 2:
                fft_mags = []
                fft_phases = []
                freqs = None
                for i in range(value.shape[0]):
                    mag, phase, f = compute_fft(value[i], dt)
                    fft_mags.append(mag)
                    fft_phases.append(phase)
                    if i == 0:
                        freqs = f
                
                self._t_vector = freqs
                self._current_phase_data = np.array(fft_phases)
                self._ensure_phase_curves(value.shape[0])
                super()._update_2d_data(np.array(fft_mags), dtype, shape, source_info + " (FFT)")
                self._plot_widget.setLabel('bottom', 'Frequency (Hz)' if is_waveform else 'FFT Bin')
                self._render_phase_curves_full()
            
            if getattr(self, '_first_data', False):
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(50, self.reset_view)
                self._first_data = False

        elif isinstance(value, dict) and value.get('__dtype__') == DTYPE_WAVEFORM_COLLECTION:
            import scipy.signal
            new_waveforms = []
            phase_waveforms = []
            for wf in value.get('waveforms', []):
                samples = np.asarray(wf['samples'])
                scalars = wf.get('scalars', [0.0, 1.0])
                dt_val = scalars[1]
                n = len(samples)
                if n > 0:
                    window = scipy.signal.windows.kaiser(n, beta=9)
                    windowed = samples * window
                    nfft = max(8192, 2**int(np.ceil(np.log2(n))))
                    fft_data = np.fft.fftshift(np.fft.fft(windowed, n=nfft))
                    fft_mag = 20 * np.log10(np.abs(fft_data) + 1e-12) - 20 * np.log10(nfft)
                    fft_phase = np.rad2deg(np.angle(fft_data))
                    
                    new_dt = 1.0 / (nfft * dt_val) if dt_val > 0 else 1.0
                    freqs = np.fft.fftshift(np.fft.fftfreq(nfft, d=dt_val)) if dt_val > 0 else np.arange(-nfft//2, nfft - nfft//2)
                    new_t0 = freqs[0]
                    if dt_val <= 0:
                        new_dt = freqs[1] - freqs[0] if len(freqs) > 1 else 1.0
                    
                    new_waveforms.append({'samples': fft_mag, 'scalars': [new_t0, new_dt]})
                    phase_waveforms.append({'samples': fft_phase, 'freqs': freqs})
            
            new_value = {'__dtype__': DTYPE_WAVEFORM_COLLECTION, 'waveforms': new_waveforms}
            super().update_data(new_value, dtype, shape, source_info + " (FFT)")
            self._plot_widget.setLabel('bottom', 'Frequency (Hz)')
            
            self._current_phase_data = None
            self._ensure_phase_curves(len(phase_waveforms))
            self._updating_curves = True
            for idx, wf in enumerate(phase_waveforms):
                x_idx, y_display = self.downsample(wf['samples'])
                self._phase_curves[idx].setData(wf['freqs'][x_idx], y_display)
            self._updating_curves = False
            
            if getattr(self, '_first_data', False):
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(50, self.reset_view)
                self._first_data = False
            
        elif isinstance(value, dict) and value.get('__dtype__') == DTYPE_ARRAY_COLLECTION:
            import scipy.signal
            new_arrays = []
            phase_arrays = []
            for arr in value.get('arrays', []):
                samples = np.asarray(arr)
                n = len(samples)
                if n > 0:
                    window = scipy.signal.windows.kaiser(n, beta=9)
                    windowed = samples * window
                    nfft = max(8192, 2**int(np.ceil(np.log2(n))))
                    fft_data = np.fft.fftshift(np.fft.fft(windowed, n=nfft))
                    fft_mag = 20 * np.log10(np.abs(fft_data) + 1e-12) - 20 * np.log10(nfft)
                    fft_phase = np.rad2deg(np.angle(fft_data))
                    new_arrays.append(fft_mag)
                    phase_arrays.append(fft_phase)
            
            new_value = {'__dtype__': DTYPE_ARRAY_COLLECTION, 'arrays': new_arrays}
            super().update_data(new_value, dtype, shape, source_info + " (FFT)")
            self._plot_widget.setLabel('bottom', 'FFT Bin')
            
            self._current_phase_data = None
            self._ensure_phase_curves(len(phase_arrays))
            self._updating_curves = True
            for idx, arr in enumerate(phase_arrays):
                x_display, y_display = self.downsample(arr)
                self._phase_curves[idx].setData(x_display, y_display)
            self._updating_curves = False
            
            if getattr(self, '_first_data', False):
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(50, self.reset_view)
                self._first_data = False
        else:
            super().update_data(value, dtype, shape, source_info)

class WaveformFftMagAnglePlugin(ProbePlugin):
    """Plugin for FFT Magnitude of 1D arrays and waveforms."""
    
    name = "FFT Mag (dB) / Angle (deg)"
    icon = "activity"
    priority = 90  # Just below Waveform
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype in (DTYPE_ARRAY_1D, DTYPE_ARRAY_2D, DTYPE_WAVEFORM_REAL, DTYPE_WAVEFORM_COLLECTION, DTYPE_ARRAY_COLLECTION)
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None) -> QWidget:
        return WaveformFftMagAngleWidget(var_name, color, parent)
    
    def update(self, widget: QWidget, value: Any, dtype: str,
               shape: Optional[Tuple[int, ...]] = None,
               source_info: str = "") -> None:
        if isinstance(widget, WaveformFftMagAngleWidget):
            widget.update_data(value, dtype, shape, source_info)

class WaveformPlugin(ProbePlugin):
    """Plugin for visualizing 1D arrays as waveforms."""
    
    name = "Waveform"
    icon = "waveform"
    priority = 100  # High priority for 1D arrays
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        # User requested specific plugins for complex data
        return dtype in (DTYPE_ARRAY_1D, DTYPE_ARRAY_2D, DTYPE_WAVEFORM_REAL, DTYPE_WAVEFORM_COLLECTION, DTYPE_ARRAY_COLLECTION)
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None) -> QWidget:
        return WaveformWidget(var_name, color, parent)
    
    def update(self, widget: QWidget, value: Any, dtype: str,
               shape: Optional[Tuple[int, ...]] = None,
               source_info: str = "") -> None:
        if isinstance(widget, WaveformWidget):
            widget.update_data(value, dtype, shape, source_info)
