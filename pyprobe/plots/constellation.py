"""
Constellation diagram for complex (I/Q) signal visualization.
Essential for DSP debugging of modulation schemes.
"""

from typing import Optional, List
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QFont

from .base_plot import BasePlot


class ConstellationPlot(BasePlot):
    """
    Real-time constellation diagram for complex arrays.

    Features:
    - Scatter plot of Real vs Imaginary
    - Reference grid
    - Power calculation in dB
    - Symbol history with fade effect
    """

    MAX_DISPLAY_POINTS = 10000
    HISTORY_LENGTH = 5  # Number of frames to show with fading

    def __init__(self, var_name: str, parent: Optional[QWidget] = None):
        super().__init__(var_name, parent)

        self._data: Optional[np.ndarray] = None
        self._history: List[np.ndarray] = []
        self._setup_ui()

    def _setup_ui(self):
        """Create the constellation plot widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Header
        header = QHBoxLayout()

        self._name_label = QLabel(self._var_name)
        self._name_label.setFont(QFont("JetBrains Mono", 11, QFont.Weight.Bold))
        self._name_label.setStyleSheet("color: #ff00ff;")  # Magenta
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

        # Stats bar (power, etc.)
        self._stats_label = QLabel("Power: -- dB | Symbols: --")
        self._stats_label.setFont(QFont("JetBrains Mono", 9))
        self._stats_label.setStyleSheet("color: #00ffff;")
        layout.addWidget(self._stats_label)

    def _configure_plot(self):
        """Configure the constellation plot appearance."""
        self._plot_widget.setBackground('#0d0d0d')
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Disable OpenGL for consistent rendering
        self._plot_widget.useOpenGL(False)

        # Set equal aspect ratio for proper constellation display
        self._plot_widget.setAspectLocked(True)

        # Configure axes
        self._plot_widget.setLabel('left', 'Q (Imag)')
        self._plot_widget.setLabel('bottom', 'I (Real)')

        # Style axes
        axis_pen = pg.mkPen(color='#ff00ff', width=1)
        self._plot_widget.getAxis('left').setPen(axis_pen)
        self._plot_widget.getAxis('bottom').setPen(axis_pen)
        self._plot_widget.getAxis('left').setTextPen(axis_pen)
        self._plot_widget.getAxis('bottom').setTextPen(axis_pen)

        # Add cross-hair at origin
        self._plot_widget.addLine(x=0, pen=pg.mkPen('#333333', width=1))
        self._plot_widget.addLine(y=0, pen=pg.mkPen('#333333', width=1))

        # Create scatter plot items for history (fading effect)
        self._scatter_items: List[pg.ScatterPlotItem] = []
        alphas = np.linspace(0.1, 1.0, self.HISTORY_LENGTH)

        for i, alpha in enumerate(alphas):
            scatter = pg.ScatterPlotItem(
                pen=None,
                brush=pg.mkBrush(0, 255, 0, int(alpha * 255)),  # Green with varying alpha
                size=4 if i < self.HISTORY_LENGTH - 1 else 6
            )
            self._plot_widget.addItem(scatter)
            self._scatter_items.append(scatter)

    def update_data(
        self,
        value: np.ndarray,
        dtype: str,
        shape: Optional[tuple] = None,
        source_info: str = ""
    ):
        """Update the constellation with new complex data."""
        if value is None:
            return

        # Convert to numpy array if needed
        if not isinstance(value, np.ndarray):
            try:
                value = np.asarray(value)
            except (ValueError, TypeError):
                return

        # Flatten
        self._data = value.flatten()

        # Ensure complex
        if not np.issubdtype(self._data.dtype, np.complexfloating):
            # If real, treat as I channel only
            self._data = self._data.astype(np.complex128)

        # Update history
        self._history.append(self._data.copy())
        if len(self._history) > self.HISTORY_LENGTH:
            self._history.pop(0)

        # Downsample if needed
        display_data = [self._downsample(d) for d in self._history]

        # Offset so newest data goes to brightest scatter (last scatter item has alpha=1.0)
        offset = len(self._scatter_items) - len(display_data)

        # Clear all scatter items first
        for scatter in self._scatter_items:
            scatter.setData(x=[], y=[])

        # Update scatter plots starting from offset position
        for i, data in enumerate(display_data):
            scatter_idx = offset + i
            if 0 <= scatter_idx < len(self._scatter_items):
                self._scatter_items[scatter_idx].setData(
                    x=data.real,
                    y=data.imag
                )

        # Update info
        shape_str = f"[{value.shape}]" if shape else ""
        self._info_label.setText(f"{shape_str} {source_info}")

        # Update stats
        self._update_stats()

    def _downsample(self, data: np.ndarray) -> np.ndarray:
        """Randomly subsample for display."""
        if len(data) <= self.MAX_DISPLAY_POINTS:
            return data
        indices = np.random.choice(len(data), self.MAX_DISPLAY_POINTS, replace=False)
        return data[indices]

    def _update_stats(self):
        """Update constellation statistics."""
        if self._data is None or len(self._data) == 0:
            return

        # Calculate signal power in dB
        power = np.mean(np.abs(self._data) ** 2)
        power_db = 10 * np.log10(power) if power > 0 else -np.inf

        self._stats_label.setText(f"Power: {power_db:.2f} dB | Symbols: {len(self._data)}")
