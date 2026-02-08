"""Constellation diagram plugin for complex arrays."""
from typing import Any, Optional, Tuple, List
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QFont, QColor

from ..base import ProbePlugin
from ...core.data_classifier import DTYPE_ARRAY_COMPLEX


class ConstellationWidget(QWidget):
    """Scatter plot widget for I/Q data."""
    
    MAX_DISPLAY_POINTS = 10000
    HISTORY_LENGTH = 5  # Number of frames to show with fading
    
    def __init__(self, var_name: str, color: QColor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._var_name = var_name
        self._color = color
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
        self._name_label.setStyleSheet(f"color: {self._color.name()};")
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
        self._stats_label = QLabel("Power: -- dB | Symbols: --")
        self._stats_label.setFont(QFont("JetBrains Mono", 9))
        self._stats_label.setStyleSheet(f"color: {self._color.name()};")
        layout.addWidget(self._stats_label)
    
    def _configure_plot(self):
        """Configure the constellation plot appearance."""
        self._plot_widget.setBackground('#0d0d0d')
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.useOpenGL(False)
        self._plot_widget.setAspectLocked(True)
        
        # Configure axes
        self._plot_widget.setLabel('left', 'Q (Imag)')
        self._plot_widget.setLabel('bottom', 'I (Real)')
        
        axis_pen = pg.mkPen(color=self._color.name(), width=1)
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
        
        r, g, b, _ = self._color.getRgb()
        
        for i, alpha in enumerate(alphas):
            scatter = pg.ScatterPlotItem(
                pen=None,
                brush=pg.mkBrush(r, g, b, int(alpha * 255)),
                size=4 if i < self.HISTORY_LENGTH - 1 else 6
            )
            self._plot_widget.addItem(scatter)
            self._scatter_items.append(scatter)

    def downsample(self, data: np.ndarray) -> np.ndarray:
        """Randomly subsample for display."""
        if len(data) <= self.MAX_DISPLAY_POINTS:
            return data
        indices = np.random.choice(len(data), self.MAX_DISPLAY_POINTS, replace=False)
        return data[indices]

    def update_data(self, value: Any, dtype: str, shape: Optional[tuple] = None, source_info: str = "") -> None:
        """Update the constellation with new complex data."""
        import sys
        print(f"[CONSTELLATION DEBUG] update_data called: value type={type(value)}", file=sys.__stderr__)
        
        if value is None:
            print(f"[CONSTELLATION DEBUG]   value is None, returning", file=sys.__stderr__)
            return
        
        if not isinstance(value, np.ndarray):
            try:
                value = np.asarray(value)
            except (ValueError, TypeError):
                print(f"[CONSTELLATION DEBUG]   failed to convert to array", file=sys.__stderr__)
                return
        
        self._data = value.flatten()
        print(f"[CONSTELLATION DEBUG]   _data shape={self._data.shape}, dtype={self._data.dtype}", file=sys.__stderr__)
        
        if not np.issubdtype(self._data.dtype, np.complexfloating):
            self._data = self._data.astype(np.complex128)
            
        self._history.append(self._data.copy())
        if len(self._history) > self.HISTORY_LENGTH:
            self._history.pop(0)
        
        print(f"[CONSTELLATION DEBUG]   history length={len(self._history)}", file=sys.__stderr__)
            
        display_data = [self.downsample(d) for d in self._history]
        
        # Offset so newest data goes to brightest scatter (last scatter item has alpha=1.0)
        # e.g. with 1 item in history, put it in scatter[4] (brightest)
        # with 3 items, put them in scatter[2], scatter[3], scatter[4]
        offset = len(self._scatter_items) - len(display_data)
        
        # Clear all scatter items first
        for scatter in self._scatter_items:
            scatter.setData(x=[], y=[])
        
        # Set data starting from offset position
        for i, data in enumerate(display_data):
            scatter_idx = offset + i
            if 0 <= scatter_idx < len(self._scatter_items):
                print(f"[CONSTELLATION DEBUG]   setting scatter[{scatter_idx}] with {len(data)} points", file=sys.__stderr__)
                self._scatter_items[scatter_idx].setData(x=data.real, y=data.imag)
        
        # Force autoRange to ensure data is visible
        self._plot_widget.autoRange()
        print(f"[CONSTELLATION DEBUG]   autoRange() called", file=sys.__stderr__)
            
        shape_str = f"[{value.shape}]" if shape else ""
        self._info_label.setText(f"{shape_str} {source_info}")
        self._update_stats()
        print(f"[CONSTELLATION DEBUG]   update complete", file=sys.__stderr__)

    def _update_stats(self):
        """Update constellation statistics."""
        if self._data is None or len(self._data) == 0:
            return
        
        power = np.mean(np.abs(self._data) ** 2)
        power_db = 10 * np.log10(power) if power > 0 else -np.inf
        
        self._stats_label.setText(f"Power: {power_db:.2f} dB | Symbols: {len(self._data)}")


class ConstellationPlugin(ProbePlugin):
    """Plugin for visualizing complex arrays as constellation diagrams."""
    
    name = "Constellation"
    icon = "constellation"
    priority = 100  # High priority for complex arrays
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        # TODO: Handle Waveform objects that are complex
        return dtype == DTYPE_ARRAY_COMPLEX
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None) -> QWidget:
        return ConstellationWidget(var_name, color, parent)
    
    def update(self, widget: QWidget, value: Any, dtype: str,
               shape: Optional[Tuple[int, ...]] = None,
               source_info: str = "") -> None:
        if isinstance(widget, ConstellationWidget):
            widget.update_data(value, dtype, shape, source_info)
