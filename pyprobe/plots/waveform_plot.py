"""
PyQtGraph-based waveform plot for 1D arrays.
Optimized for real-time DSP visualization.
"""

from typing import Optional
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QFont
from ..core.data_classifier import DTYPE_WAVEFORM_REAL, get_waveform_info

from .base_plot import BasePlot


class WaveformPlot(BasePlot):
    """
    Real-time waveform plot for 1D arrays.

    Features:
    - Auto-scaling Y axis
    - Downsampling for large arrays (maintains visual fidelity)
    - Statistics display (min, max, mean)
    """

    # Maximum points to display (downsample if larger)
    MAX_DISPLAY_POINTS = 5000

    def __init__(self, var_name: str, parent: Optional[QWidget] = None):
        super().__init__(var_name, parent)

        self._data: Optional[np.ndarray] = None
        self._t_vector: Optional[np.ndarray] = None  # For Waveform objects
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

        # Create plot curve (disable antialias for performance)
        self._curve = self._plot_widget.plot(
            pen=pg.mkPen(color='#00ff00', width=1.5),  # Green
            antialias=False
        )

        # Enable mouse interaction
        self._plot_widget.setMouseEnabled(x=True, y=True)

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

        # Handle waveform objects (2 scalars + 1 array)
        t_vector = None
        
        # Serialized waveform from IPC
        if isinstance(value, dict) and value.get('__dtype__') == DTYPE_WAVEFORM_REAL:
            samples = np.asarray(value['samples'])
            scalars = value.get('scalars', [0.0, 1.0])  # [t0, dt] sorted
            t0, dt = scalars[0], scalars[1]
            t_vector = t0 + np.arange(len(samples)) * dt
            value = samples
        else:
            # Check for direct waveform object
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

        self._data = value.flatten() if value.ndim > 1 else value
        self._t_vector = t_vector  # Store for plotting

        # Downsample if needed
        display_data = self._downsample(self._data)

        # Update plot - use time vector if available (Waveform objects)
        if self._t_vector is not None and len(self._t_vector) == len(self._data):
            # Downsample time vector to match
            t_display = self._downsample(self._t_vector) if len(self._data) > self.MAX_DISPLAY_POINTS else self._t_vector
            self._curve.setData(t_display, display_data)
            self._plot_widget.setLabel('bottom', 'Time')
        else:
            self._curve.setData(display_data)
            self._plot_widget.setLabel('bottom', 'Sample Index')

        # Update info label
        shape_str = f"[{value.shape}]" if shape else ""
        self._info_label.setText(f"{shape_str} {source_info}")

        # Update stats
        self._update_stats()

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
        """Update statistics display."""
        if self._data is None or len(self._data) == 0:
            return

        min_val = np.min(self._data)
        max_val = np.max(self._data)
        mean_val = np.mean(self._data)

        self._stats_label.setText(
            f"Min: {min_val:.4g} | Max: {max_val:.4g} | Mean: {mean_val:.4g}"
        )
