"""
PyQtGraph-based waveform plot for 1D and 2D arrays.
Optimized for real-time DSP visualization.
"""

from typing import Optional, List
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QFont
from ..core.data_classifier import (
    DTYPE_WAVEFORM_REAL, DTYPE_WAVEFORM_COLLECTION, DTYPE_ARRAY_2D,
    get_waveform_info, get_waveform_collection_info
)

from .base_plot import BasePlot


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


class WaveformPlot(BasePlot):
    """
    Real-time waveform plot for 1D and 2D arrays.

    Features:
    - Auto-scaling Y axis
    - Downsampling for large arrays (maintains visual fidelity)
    - Statistics display (min, max, mean)
    - Multi-row support for 2D arrays with deterministic colors
    - Clickable legend to toggle row visibility
    """

    # Maximum points to display per row (downsample if larger)
    MAX_DISPLAY_POINTS = 5000

    def __init__(self, var_name: str, parent: Optional[QWidget] = None):
        super().__init__(var_name, parent)

        self._data: Optional[np.ndarray] = None
        self._t_vector: Optional[np.ndarray] = None  # For Waveform objects
        self._curves: List[pg.PlotDataItem] = []  # Multiple curves for 2D
        self._row_visible: List[bool] = []  # Track visibility per row
        self._legend: Optional[pg.LegendItem] = None
        self._setup_ui()

    def _setup_ui(self):
        """Create the plot widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Header with variable name and info
        header = QHBoxLayout()

        self._name_label = QLabel(self._var_name)
        self._name_label.setFont(QFont("JetBrains Mono", 11, QFont.Weight.Bold))
        self._name_label.setStyleSheet("color: #00ffff;")  # Cyan
        header.addWidget(self._name_label)

        header.addStretch()

        self._info_label = QLabel("")
        self._info_label.setFont(QFont("JetBrains Mono", 9))
        self._info_label.setStyleSheet("color: #888888;")
        header.addWidget(self._info_label)

        layout.addLayout(header)

        # PyQtGraph plot widget
        self._plot_widget = pg.PlotWidget()
        self._configure_plot()
        layout.addWidget(self._plot_widget)

        # Stats bar
        self._stats_label = QLabel("Min: -- | Max: -- | Mean: --")
        self._stats_label.setFont(QFont("JetBrains Mono", 9))
        self._stats_label.setStyleSheet("color: #ff00ff;")  # Magenta
        layout.addWidget(self._stats_label)

    def _configure_plot(self):
        """Configure PyQtGraph plot appearance."""
        self._plot_widget.setBackground('#0d0d0d')
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Disable OpenGL for consistent rendering
        self._plot_widget.useOpenGL(False)

        # Configure axes
        self._plot_widget.setLabel('left', 'Amplitude')
        self._plot_widget.setLabel('bottom', 'Sample Index')

        # Style axes
        axis_pen = pg.mkPen(color='#00ffff', width=1)
        self._plot_widget.getAxis('left').setPen(axis_pen)
        self._plot_widget.getAxis('bottom').setPen(axis_pen)
        self._plot_widget.getAxis('left').setTextPen(axis_pen)
        self._plot_widget.getAxis('bottom').setTextPen(axis_pen)

        # Create initial single curve (for 1D data)
        self._curves = [self._plot_widget.plot(
            pen=pg.mkPen(color=ROW_COLORS[0], width=1.5),
            antialias=False
        )]
        self._row_visible = [True]

        # Enable mouse interaction
        self._plot_widget.setMouseEnabled(x=True, y=True)

    def _get_row_color(self, row_index: int) -> str:
        """Get deterministic color for row index (cycles after 10)."""
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
            # pyqtgraph LegendItem doesn't have built-in click toggle,
            # so we implement it via the curve's visibility
            for idx, item in enumerate(self._legend.items):
                label = item[1]
                label.setAttr('idx', idx)
                label.mousePressEvent = lambda ev, i=idx: self._toggle_row(i)

    def _toggle_row(self, row_index: int):
        """Toggle visibility of a row."""
        if row_index < len(self._curves):
            self._row_visible[row_index] = not self._row_visible[row_index]
            self._curves[row_index].setVisible(self._row_visible[row_index])

    def update_data(
        self,
        value: np.ndarray,
        dtype: str,
        shape: Optional[tuple] = None,
        source_info: str = ""
    ):
        """Update the plot with new data."""
        if value is None:
            return

        # Handle serialized waveform collection from IPC
        if isinstance(value, dict) and value.get('__dtype__') == DTYPE_WAVEFORM_COLLECTION:
            self._update_waveform_collection_data(value, dtype, shape, source_info)
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
                    scalars = sorted([float(getattr(obj, attr)) for attr in info['scalar_attrs']])
                    serialized['waveforms'].append({'samples': samples, 'scalars': scalars})
                self._update_waveform_collection_data(serialized, dtype, shape, source_info)
                return

            # Check for direct single waveform object
            waveform_info = get_waveform_info(value)
            if waveform_info is not None:
                samples_attr = waveform_info['samples_attr']
                scalar_attrs = waveform_info['scalar_attrs']
                samples = np.asarray(getattr(value, samples_attr))
                scalars = sorted([float(getattr(value, attr)) for attr in scalar_attrs])
                t0, dt = scalars[0], scalars[1]
                t_vector = t0 + np.arange(len(samples)) * dt
                value = samples

        # Convert to numpy array if needed
        if not isinstance(value, np.ndarray):
            try:
                value = np.asarray(value)
            except (ValueError, TypeError):
                return

        self._t_vector = t_vector

        # Handle 2D arrays: each row is a separate time series
        if value.ndim == 2:
            self._update_2d_data(value, dtype, shape, source_info)
        else:
            self._update_1d_data(value, dtype, shape, source_info)

    def _update_1d_data(
        self,
        value: np.ndarray,
        dtype: str,
        shape: Optional[tuple],
        source_info: str
    ):
        """Update plot with 1D data."""
        self._data = value.flatten() if value.ndim > 1 else value
        
        # Ensure single curve
        self._ensure_curves(1)

        # Downsample if needed
        display_data = self._downsample(self._data)

        # Update plot - use time vector if available (Waveform objects)
        if self._t_vector is not None and len(self._t_vector) == len(self._data):
            t_display = self._downsample(self._t_vector) if len(self._data) > self.MAX_DISPLAY_POINTS else self._t_vector
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

    def _update_2d_data(
        self,
        value: np.ndarray,
        dtype: str,
        shape: Optional[tuple],
        source_info: str
    ):
        """Update plot with 2D data (each row is a time series)."""
        num_rows = value.shape[0]
        self._data = value  # Store full 2D array
        
        # Ensure correct number of curves
        self._ensure_curves(num_rows)

        # Update each row
        for row_idx in range(num_rows):
            row_data = value[row_idx, :]
            display_data = self._downsample(row_data)
            
            if self._t_vector is not None and len(self._t_vector) == len(row_data):
                t_display = self._downsample(self._t_vector) if len(row_data) > self.MAX_DISPLAY_POINTS else self._t_vector
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

    def _downsample(self, data: np.ndarray) -> np.ndarray:
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
        truncated = data[:n_chunks * chunk_size]
        reshaped = truncated.reshape(n_chunks, chunk_size)

        mins = reshaped.min(axis=1)
        maxs = reshaped.max(axis=1)

        # Interleave min and max
        result = np.empty(n_chunks * 2, dtype=data.dtype)
        result[0::2] = mins
        result[1::2] = maxs

        return result

    def _update_stats(self):
        """Update statistics display for 1D data."""
        if self._data is None or len(self._data) == 0:
            return

        min_val = np.min(self._data)
        max_val = np.max(self._data)
        mean_val = np.mean(self._data)

        self._stats_label.setText(
            f"Min: {min_val:.4g} | Max: {max_val:.4g} | Mean: {mean_val:.4g}"
        )

    def _update_stats_2d(self):
        """Update statistics display for 2D data (aggregate)."""
        if self._data is None or self._data.size == 0:
            return

        min_val = np.min(self._data)
        max_val = np.max(self._data)
        mean_val = np.mean(self._data)
        num_rows = self._data.shape[0]

        self._stats_label.setText(
            f"{num_rows} rows | Min: {min_val:.4g} | Max: {max_val:.4g} | Mean: {mean_val:.4g}"
        )

    def _update_waveform_collection_data(
        self,
        value: dict,
        dtype: str,
        shape: Optional[tuple],
        source_info: str
    ):
        """Update plot with waveform collection (each waveform has its own t0, dt, samples)."""
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
            
            display_data = self._downsample(samples)
            t_display = self._downsample(t_vector) if len(samples) > self.MAX_DISPLAY_POINTS else t_vector
            
            self._curves[idx].setData(t_display, display_data)
            all_samples.append(samples)

        # Set x-axis label (always Time for waveform collections)
        self._plot_widget.setLabel('bottom', 'Time')

        # Update info label
        self._info_label.setText(f"[{num_waveforms} waveforms] {source_info}")

        # Update stats (aggregate across all waveforms)
        if all_samples:
            all_data = np.concatenate(all_samples)
            min_val = np.min(all_data)
            max_val = np.max(all_data)
            mean_val = np.mean(all_data)
            self._stats_label.setText(
                f"{num_waveforms} wfms | Min: {min_val:.4g} | Max: {max_val:.4g} | Mean: {mean_val:.4g}"
            )


