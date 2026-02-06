"""
Scalar history chart for trending scalar values over time.

Implements LabVIEW Waveform Chart-style behavior:
- FIFO history buffer with configurable length
- Strip-chart scrolling (auto-scroll left as new values arrive)
- Real-time trending for convergence debugging
"""

from collections import deque
from typing import Optional, Any
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QFont

from .base_plot import BasePlot


class ScalarHistoryChart(BasePlot):
    """
    Real-time scrolling chart for scalar values.

    Features:
    - Auto-scrolling strip chart (LabVIEW Waveform Chart style)
    - FIFO history buffer (configurable length)
    - Auto-ranging Y-axis
    - Current value + min/max/mean statistics
    """

    DEFAULT_HISTORY_LENGTH = 512

    def __init__(
        self,
        var_name: str,
        parent: Optional[QWidget] = None,
        history_length: int = DEFAULT_HISTORY_LENGTH
    ):
        super().__init__(var_name, parent)

        self._history: deque = deque(maxlen=history_length)
        self._has_data = False
        self._setup_ui()

    def _setup_ui(self):
        """Create the chart widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Header with variable name and current value
        header = QHBoxLayout()

        self._name_label = QLabel(self._var_name)
        self._name_label.setFont(QFont("JetBrains Mono", 11, QFont.Weight.Bold))
        self._name_label.setStyleSheet("color: #ffff00;")  # Yellow
        header.addWidget(self._name_label)

        header.addStretch()

        # Current value display (large, prominent)
        self._value_label = QLabel("--")
        self._value_label.setFont(QFont("JetBrains Mono", 14, QFont.Weight.Bold))
        self._value_label.setStyleSheet("color: #00ff00;")  # Green
        header.addWidget(self._value_label)

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
        self._plot_widget.setLabel('left', 'Value')
        self._plot_widget.setLabel('bottom', 'Sample')

        # Style axes - yellow to match variable name
        axis_pen = pg.mkPen(color='#ffff00', width=1)
        self._plot_widget.getAxis('left').setPen(axis_pen)
        self._plot_widget.getAxis('bottom').setPen(axis_pen)
        self._plot_widget.getAxis('left').setTextPen(axis_pen)
        self._plot_widget.getAxis('bottom').setTextPen(axis_pen)

        # Create plot curve
        self._curve = self._plot_widget.plot(
            pen=pg.mkPen(color='#00ff00', width=2),  # Green
            antialias=False
        )

        # Enable mouse interaction
        self._plot_widget.setMouseEnabled(x=True, y=True)

    def update_data(
        self,
        value: Any,
        dtype: str,
        shape: Optional[tuple] = None,
        source_info: str = ""
    ):
        """Update the chart with a new scalar value."""
        if value is None:
            return

        # Convert to float for plotting
        try:
            if isinstance(value, complex):
                # For complex, plot magnitude
                float_value = abs(value)
            elif isinstance(value, np.ndarray) and value.ndim == 0:
                # 0-dim numpy array
                float_value = float(value.item())
            else:
                float_value = float(value)
        except (ValueError, TypeError):
            return

        # Mark as having data on first update
        if not self._has_data:
            self._has_data = True

        # Append to FIFO history
        self._history.append(float_value)

        # Update plot
        self._curve.setData(list(self._history))

        # Update current value display
        self._value_label.setText(f"{float_value:.6g}")

        # Update stats
        self._update_stats()

    def _update_stats(self):
        """Update min/max/mean statistics display."""
        if not self._history:
            return

        # Convert to numpy for efficient stats
        data = np.array(self._history)
        min_val = np.min(data)
        max_val = np.max(data)
        mean_val = np.mean(data)

        self._stats_label.setText(
            f"Min: {min_val:.4g} | Max: {max_val:.4g} | Mean: {mean_val:.4g}"
        )

    def clear_history(self):
        """Clear the history buffer and reset the display."""
        self._history.clear()
        self._curve.setData([])
        self._value_label.setText("--")
        self._stats_label.setText("Min: -- | Max: -- | Mean: --")
        self._has_data = False
