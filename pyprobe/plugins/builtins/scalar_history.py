"""Scalar history chart plugin - shows value over time."""
from typing import Any, Optional, Tuple
from collections import deque
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import QRectF, QTimer

from ..base import ProbePlugin
from ...core.data_classifier import DTYPE_SCALAR
from ...plots.axis_controller import AxisController
from ...plots.pin_indicator import PinIndicator


class ScalarHistoryWidget(QWidget):
    """Chart showing scalar values over multiple frames."""
    
    DEFAULT_HISTORY_LENGTH = 512
    
    def __init__(self, var_name: str, color: QColor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._var_name = var_name
        self._color = color
        self._history: deque = deque(maxlen=self.DEFAULT_HISTORY_LENGTH)
        self._has_data = False
        
        # Axis pinning
        self._axis_controller: Optional[AxisController] = None
        self._pin_indicator: Optional[PinIndicator] = None
        
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

        # Setup axis controller and pin indicator
        plot_item = self._plot_widget.getPlotItem()
        self._axis_controller = AxisController(plot_item)
        self._axis_controller.pin_state_changed.connect(self._on_pin_state_changed)

        self._pin_indicator = PinIndicator(self)
        self._pin_indicator.x_pin_clicked.connect(lambda: self._axis_controller.toggle_pin('x'))
        self._pin_indicator.y_pin_clicked.connect(lambda: self._axis_controller.toggle_pin('y'))
        self._pin_indicator.raise_()
        self._pin_indicator.show()

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

    def update_history(self, values: list) -> None:
        """Replace history with full buffer and redraw."""
        if not values:
            return

        converted = []
        for value in values:
            try:
                if isinstance(value, complex):
                    converted.append(abs(value))
                elif isinstance(value, np.ndarray) and value.ndim == 0:
                    converted.append(float(value.item()))
                else:
                    converted.append(float(value))
            except (ValueError, TypeError):
                return

        self._has_data = True
        self._history = deque(converted, maxlen=self.DEFAULT_HISTORY_LENGTH)
        
        # Update plot
        self._curve.setData(list(self._history))
        
        # Update current value
        if converted:
             self._value_label.setText(f"{converted[-1]:.6g}")

        # Update stats
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

    def get_plot_data(self) -> dict:
        """
        Return the data currently plotted on the graph.
        
        Returns the internal history buffer directly (more reliable
        than curve.getData() which may have timing issues).
        
        Returns:
            dict with 'x' and 'y' keys containing lists of values
        """
        y_data = list(self._history)
        x_data = list(range(len(y_data)))
        return {'x': x_data, 'y': y_data}


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
