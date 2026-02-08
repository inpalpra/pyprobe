"""Waveform visualization plugin for 1D arrays."""
from typing import Any, Optional, Tuple, List
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import QRectF

from ..base import ProbePlugin
from ...core.data_classifier import (
    DTYPE_ARRAY_1D, DTYPE_ARRAY_2D, DTYPE_ARRAY_COMPLEX,
    DTYPE_WAVEFORM_REAL, DTYPE_WAVEFORM_COLLECTION, DTYPE_ARRAY_COLLECTION,
    get_waveform_info, get_waveform_collection_info
)
from ...plots.axis_controller import AxisController
from ...plots.pin_indicator import PinIndicator

# Deterministic color palette for multi-row plots (10 colors, cycling)
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


class WaveformWidget(QWidget):
    """The actual plot widget created by WaveformPlugin."""
    
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
        
        self._setup_ui()
    
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
        self._info_label.setStyleSheet("color: #888888;")
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
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.useOpenGL(False)
        
        # Configure axes
        self._plot_widget.setLabel('left', 'Amplitude')
        self._plot_widget.setLabel('bottom', 'Sample Index')
        
        axis_pen = pg.mkPen(color=self._color.name(), width=1)
        self._plot_widget.getAxis('left').setPen(axis_pen)
        self._plot_widget.getAxis('bottom').setPen(axis_pen)
        self._plot_widget.getAxis('left').setTextPen(axis_pen)
        self._plot_widget.getAxis('bottom').setTextPen(axis_pen)
        
        # Create initial single curve (for 1D data) using PROBE COLOR
        self._curves = [self._plot_widget.plot(
            pen=pg.mkPen(color=self._color.name(), width=1.5),
            antialias=False
        )]
        self._row_visible = [True]
        
        self._plot_widget.setMouseEnabled(x=True, y=True)
        
        # M2.5: Setup axis controller and pin indicator
        plot_item = self._plot_widget.getPlotItem()
        self._axis_controller = AxisController(plot_item)
        self._axis_controller.pin_state_changed.connect(self._on_pin_state_changed)
        
        self._pin_indicator = PinIndicator(self)  # Parent to WaveformWidget
        self._pin_indicator.x_pin_clicked.connect(lambda: self._axis_controller.toggle_pin('x'))
        self._pin_indicator.y_pin_clicked.connect(lambda: self._axis_controller.toggle_pin('y'))
        self._pin_indicator.raise_()
        self._pin_indicator.show()
    
    def _on_pin_state_changed(self, axis: str, is_pinned: bool) -> None:
        """Handle axis pin state change from AxisController."""
        if self._pin_indicator:
            self._pin_indicator.update_state(axis, is_pinned)
    
    @property
    def axis_controller(self) -> Optional[AxisController]:
        """Access the axis controller for external use (e.g., keyboard shortcuts)."""
        return self._axis_controller
    
    def showEvent(self, event) -> None:
        """Trigger layout update when widget is shown."""
        super().showEvent(event)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._update_pin_layout)

    def resizeEvent(self, event) -> None:
        """Reposition pin indicator buttons on resize."""
        super().resizeEvent(event)
        self._update_pin_layout()

    def _update_pin_layout(self) -> None:
        """Update the position of pin indicators."""
        if self._pin_indicator and self._plot_widget:
            # Resize indicator overlay to cover full widget
            self._pin_indicator.setGeometry(0, 0, self.width(), self.height())
            
            plot_item = self._plot_widget.getPlotItem()
            
            def get_mapped_rect(item):
                scene_rect = item.sceneBoundingRect()
                view_poly = self._plot_widget.mapFromScene(scene_rect)
                view_rect = view_poly.boundingRect()
                # Map top-left to self (WaveformWidget) coordinates
                tl_mapped = self._plot_widget.mapTo(self, view_rect.topLeft())
                return QRectF(
                    float(tl_mapped.x()), float(tl_mapped.y()),
                    view_rect.width(), view_rect.height()
                )

            view_rect = get_mapped_rect(plot_item.getViewBox())
            
            self._pin_indicator.update_layout(view_rect)
            self._pin_indicator.raise_()
        
    def _get_row_color(self, row_index: int) -> str:
        """Get deterministic color for row index (cycles after 10)."""
        # For multi-row, we use the palette to distinguish rows
        return ROW_COLORS[row_index % len(ROW_COLORS)]

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
        
        # Remove excess curves if needed
        while len(self._curves) > num_rows:
            curve = self._curves.pop()
            self._row_visible.pop()
            self._plot_widget.removeItem(curve)
        
        # Create legend for multi-row (>1 row)
        if num_rows > 1:
            self._legend = self._plot_widget.addLegend(
                offset=(10, 10),
                labelTextColor='#ffffff',
                brush=pg.mkBrush('#1a1a1a80')
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

    def downsample(self, data: np.ndarray) -> np.ndarray:
        """
        Downsample data for display while preserving visual features.
        Uses min-max decimation to preserve peaks.
        """
        if len(data) <= self.MAX_DISPLAY_POINTS:
            return data

        # Number of chunks
        n_chunks = self.MAX_DISPLAY_POINTS // 2
        chunk_size = len(data) // n_chunks

        # Reshape and get min/max per chunk
        # Truncate to multiple of chunk_size
        truncated = data[:n_chunks * chunk_size]
        reshaped = truncated.reshape(n_chunks, chunk_size)

        mins = reshaped.min(axis=1)
        maxs = reshaped.max(axis=1)

        # Interleave min and max
        result = np.empty(n_chunks * 2, dtype=data.dtype)
        result[0::2] = mins
        result[1::2] = maxs

        return result

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

        # Downsample if needed
        display_data = self.downsample(self._data)

        # Update plot - use time vector if available (Waveform objects)
        if self._t_vector is not None and len(self._t_vector) == len(self._data):
            t_display = self.downsample(self._t_vector) if len(self._data) > self.MAX_DISPLAY_POINTS else self._t_vector
            self._curves[0].setData(t_display, display_data)
            self._plot_widget.setLabel('bottom', 'Time')
        else:
            self._curves[0].setData(display_data)
            self._plot_widget.setLabel('bottom', 'Sample Index')

        # Update info label
        shape_str = f"[{value.shape}]" if shape else ""
        self._info_label.setText(f"{shape_str} {source_info}")

        # Update stats
        self._update_stats()

    def _update_2d_data(self, value: np.ndarray, dtype: str, shape: Optional[tuple], source_info: str):
        """Update plot with 2D data (each row is a time series)."""
        num_rows = value.shape[0]
        self._data = value  # Store full 2D array
        
        # Ensure correct number of curves
        self._ensure_curves(num_rows)

        # Update each row
        for row_idx in range(num_rows):
            row_data = value[row_idx, :]
            display_data = self.downsample(row_data)
            
            if self._t_vector is not None and len(self._t_vector) == len(row_data):
                t_display = self.downsample(self._t_vector) if len(row_data) > self.MAX_DISPLAY_POINTS else self._t_vector
                self._curves[row_idx].setData(t_display, display_data)
            else:
                self._curves[row_idx].setData(display_data)

        # Set x-axis label
        if self._t_vector is not None:
            self._plot_widget.setLabel('bottom', 'Time')
        else:
            self._plot_widget.setLabel('bottom', 'Sample Index')

        # Update info label
        shape_str = f"[{value.shape[0]}×{value.shape[1]}]"
        self._info_label.setText(f"{shape_str} {source_info}")

        # Update stats (aggregate across all rows)
        self._update_stats_2d()

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
        for idx, wf in enumerate(waveforms):
            samples = np.asarray(wf['samples'])
            scalars = wf.get('scalars', [0.0, 1.0])
            t0, dt = scalars[0], scalars[1]
            
            # Compute time vector for this specific waveform
            t_vector = t0 + np.arange(len(samples)) * dt
            
            display_data = self.downsample(samples)
            t_display = self.downsample(t_vector) if len(samples) > self.MAX_DISPLAY_POINTS else t_vector
            
            self._curves[idx].setData(t_display, display_data)
            all_samples.append(samples)

        self._plot_widget.setLabel('bottom', 'Time')
        self._info_label.setText(f"[{num_waveforms} waveforms] {source_info}")

        if all_samples:
            all_data = np.concatenate(all_samples)
            self._update_stats_from_data(all_data, f"{num_waveforms} wfms")

    def _update_array_collection_data(self, value: dict, dtype: str, shape: Optional[tuple], source_info: str):
        """Update plot with array collection."""
        arrays = value.get('arrays', [])
        num_arrays = len(arrays)
        
        if num_arrays == 0:
            return
        
        self._ensure_curves(num_arrays)
        all_data = []

        for idx, arr in enumerate(arrays):
            samples = np.asarray(arr)
            display_data = self.downsample(samples)
            self._curves[idx].setData(display_data)
            all_data.append(samples)

        self._plot_widget.setLabel('bottom', 'Sample Index')
        self._info_label.setText(f"[{num_arrays} arrays] {source_info}")

        if all_data:
            concatenated = np.concatenate(all_data)
            self._update_stats_from_data(concatenated, f"{num_arrays} arrays")

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

    def _update_stats_from_data(self, data: np.ndarray, prefix: str = ""):
        min_val = np.min(data)
        max_val = np.max(data)
        mean_val = np.mean(data)
        
        prefix_str = f"{prefix} | " if prefix else ""
        self._stats_label.setText(
            f"{prefix_str}Min: {min_val:.4g} | Max: {max_val:.4g} | Mean: {mean_val:.4g}"
        )


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
