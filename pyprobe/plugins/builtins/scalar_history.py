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
from ...plots.editable_axis import EditableAxisItem
from ...gui.axis_editor import AxisEditor

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
        self._axis_editor: Optional[AxisEditor] = None

        self._setup_ui()

        from ...gui.theme.theme_manager import ThemeManager
        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.current)
    
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
        # Use a more visible default grid alpha (0.6) before theme override
        self._plot_widget.showGrid(x=True, y=True, alpha=0.6)
        self._plot_widget.useOpenGL(False)
        self._plot_widget.setLabel('left', 'Value')
        self._plot_widget.setLabel('bottom', 'Sample')

        axis_pen = pg.mkPen(color=self._color.name(), width=1)
        self._plot_widget.getAxis('left').setPen(axis_pen)
        self._plot_widget.getAxis('bottom').setPen(axis_pen)
        self._plot_widget.getAxis('left').setTextPen(axis_pen)
        self._plot_widget.getAxis('bottom').setTextPen(axis_pen)

        # Setup editable axes
        self._setup_editable_axes()
        
        # Axis editor (inline text editor)
        self._axis_editor = AxisEditor(self._plot_widget)
        self._axis_editor.value_committed.connect(self._on_axis_value_committed)
        self._axis_editor.editing_cancelled.connect(self._on_axis_edit_cancelled)

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

    def _apply_theme(self, theme) -> None:
        c = theme.colors
        pc = theme.plot_colors
        grid_alpha = float(pc.get('grid_alpha', 0.28))
        self._value_label.setStyleSheet(f"color: {c['text_primary']};")
        self._plot_widget.setBackground(pc['bg'])
        self._plot_widget.showGrid(x=True, y=True, alpha=grid_alpha)
        
        # manually force grid
        alpha_int = int(min(255, max(0, grid_alpha * 255)))
        axis_pen = pg.mkPen(color=pc['axis'], width=1)
        for ax_name in ('left', 'bottom'):
            ax = self._plot_widget.getAxis(ax_name)
            if ax is not None:
                ax.setPen(axis_pen)
                ax.setTextPen(axis_pen)
                if hasattr(ax, 'setGrid'):
                    ax.setGrid(alpha_int)

    def set_color(self, color: QColor) -> None:
        """Update the probe color (name label, stats, curve, axes)."""
        self._color = color
        hex_color = color.name()
        self._name_label.setStyleSheet(f"color: {hex_color};")
        self._stats_label.setStyleSheet(f"color: {hex_color};")
        self._curve.setPen(pg.mkPen(hex_color, width=2))
        axis_pen = pg.mkPen(color=hex_color, width=1)
        for ax_name in ('left', 'bottom'):
            ax = self._plot_widget.getAxis(ax_name)
            if ax is not None:
                ax.setPen(axis_pen)
                ax.setTextPen(axis_pen)

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

    def clear_history(self):
        """Clear the history buffer and reset the display."""
        self._history.clear()
        self._curve.setData([])
        self._value_label.setText("--")
        self._stats_label.setText("Min: -- | Max: -- | Mean: --")
        self._has_data = False

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

    def reset_view(self) -> None:
        """Reset the view: unpin axes, snap to full range."""
        if self._axis_controller:
            self._axis_controller.set_pinned('x', False)
            self._axis_controller.set_pinned('y', False)
        vb = self._plot_widget.getPlotItem().getViewBox()
        vb.autoRange(padding=0)

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
