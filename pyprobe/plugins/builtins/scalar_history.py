"""Scalar history chart plugin - shows value over time."""
from typing import Any, Optional, Tuple
from collections import deque
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QFont, QColor

from ..base import ProbePlugin
from ...core.data_classifier import DTYPE_SCALAR


class ScalarHistoryWidget(QWidget):
    """Chart showing scalar values over multiple frames."""
    
    DEFAULT_HISTORY_LENGTH = 512
    
    def __init__(self, var_name: str, color: QColor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._var_name = var_name
        self._color = color
        self._history: deque = deque(maxlen=self.DEFAULT_HISTORY_LENGTH)
        self._has_data = False
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the chart widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Header
        header = QHBoxLayout()
        self._name_label = QLabel(self._var_name)
        self._name_label.setFont(QFont("JetBrains Mono", 11, QFont.Weight.Bold))
        self._name_label.setStyleSheet(f"color: {self._color.name()};")
        header.addWidget(self._name_label)
        header.addStretch()
        
        self._value_label = QLabel("--")
        self._value_label.setFont(QFont("JetBrains Mono", 14, QFont.Weight.Bold))
        self._value_label.setStyleSheet("color: #ffffff;")
        header.addWidget(self._value_label)
        layout.addLayout(header)
        
        # Plot
        self._plot_widget = pg.PlotWidget()
        self._configure_plot()
        layout.addWidget(self._plot_widget)
        
        # Stats
        self._stats_label = QLabel("Min: -- | Max: -- | Mean: --")
        self._stats_label.setFont(QFont("JetBrains Mono", 9))
        self._stats_label.setStyleSheet(f"color: {self._color.name()};")
        layout.addWidget(self._stats_label)
    
    def _configure_plot(self):
        """Configure plot."""
        self._plot_widget.setBackground('#0d0d0d')
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.useOpenGL(False)
        self._plot_widget.setLabel('left', 'Value')
        self._plot_widget.setLabel('bottom', 'Sample')
        
        axis_pen = pg.mkPen(color=self._color.name(), width=1)
        self._plot_widget.getAxis('left').setPen(axis_pen)
        self._plot_widget.getAxis('bottom').setPen(axis_pen)
        self._plot_widget.getAxis('left').setTextPen(axis_pen)
        self._plot_widget.getAxis('bottom').setTextPen(axis_pen)
        
        self._curve = self._plot_widget.plot(
            pen=pg.mkPen(color=self._color.name(), width=2),
            antialias=False
        )
        self._plot_widget.setMouseEnabled(x=True, y=True)

    def update_data(self, value: Any, dtype: str, shape: Optional[tuple] = None, source_info: str = "") -> None:
        """Update the chart with a new scalar value."""
        if value is None:
            return
        
        try:
            if isinstance(value, complex):
                float_value = abs(value)
            elif isinstance(value, np.ndarray) and value.ndim == 0:
                float_value = float(value.item())
            else:
                float_value = float(value)
        except (ValueError, TypeError):
            return
        
        if not self._has_data:
            self._has_data = True
            
        self._history.append(float_value)
        self._curve.setData(list(self._history))
        self._value_label.setText(f"{float_value:.6g}")
        self._update_stats()

    def _update_stats(self):
        """Update min/max/mean statistics."""
        if not self._history:
            return
        
        data = np.array(self._history)
        min_val = np.min(data)
        max_val = np.max(data)
        mean_val = np.mean(data)
        
        self._stats_label.setText(f"Min: {min_val:.4g} | Max: {max_val:.4g} | Mean: {mean_val:.4g}")


class ScalarHistoryPlugin(ProbePlugin):
    """Plugin for visualizing scalar values as a time-series chart."""
    
    name = "History"
    icon = "chart"
    priority = 100  # High priority for scalars
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype == DTYPE_SCALAR
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None) -> QWidget:
        return ScalarHistoryWidget(var_name, color, parent)
    
    def update(self, widget: QWidget, value: Any, dtype: str,
               shape: Optional[Tuple[int, ...]] = None,
               source_info: str = "") -> None:
        if isinstance(widget, ScalarHistoryWidget):
            widget.update_data(value, dtype, shape, source_info)
