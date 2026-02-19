"""
Constellation diagram for complex (I/Q) signal visualization.
Essential for DSP debugging of modulation schemes.
"""

from typing import Optional, List
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import QRectF

from .base_plot import BasePlot
from .axis_controller import AxisController
from .pin_indicator import PinIndicator
from .pin_layout_mixin import PinLayoutMixin


class ConstellationPlot(PinLayoutMixin, BasePlot):
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

        # Axis pinning
        self._axis_controller: Optional[AxisController] = None
        self._pin_indicator: Optional[PinIndicator] = None

        self._setup_ui()

        from pyprobe.gui.theme.theme_manager import ThemeManager
        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.current)

    def _setup_ui(self):
        """Create the constellation plot widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Header
        header = QHBoxLayout()

        self._name_label = QLabel(self._var_name)
        self._name_label.setFont(QFont("JetBrains Mono", 11, QFont.Weight.Bold))
        header.addWidget(self._name_label)

        header.addStretch()

        self._info_label = QLabel("")
        self._info_label.setFont(QFont("JetBrains Mono", 9))
        header.addWidget(self._info_label)

        layout.addLayout(header)

        # PyQtGraph plot widget
        self._plot_widget = pg.PlotWidget()
        self._configure_plot()
        layout.addWidget(self._plot_widget)

        # Stats bar (power, etc.)
        self._stats_label = QLabel("Power: -- dB | Symbols: --")
        self._stats_label.setFont(QFont("JetBrains Mono", 9))
        layout.addWidget(self._stats_label)

    def _configure_plot(self):
        """Configure the constellation plot appearance."""
        self._plot_widget.setBackground('#0d0d0d')
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.useOpenGL(False)
        self._plot_widget.setAspectLocked(True)
        self._plot_widget.setLabel('left', 'Q (Imag)')
        self._plot_widget.setLabel('bottom', 'I (Real)')

        axis_pen = pg.mkPen(color='#ff00ff', width=1)
        self._plot_widget.getAxis('left').setPen(axis_pen)
        self._plot_widget.getAxis('bottom').setPen(axis_pen)
        self._plot_widget.getAxis('left').setTextPen(axis_pen)
        self._plot_widget.getAxis('bottom').setTextPen(axis_pen)

        # Add cross-hair at origin
        self._origin_x = self._plot_widget.addLine(x=0, pen=pg.mkPen('#333333', width=1))
        self._origin_y = self._plot_widget.addLine(y=0, pen=pg.mkPen('#333333', width=1))

        # Create scatter plot items for history (fading effect)
        self._scatter_items: List[pg.ScatterPlotItem] = []
        alphas = np.linspace(0.1, 1.0, self.HISTORY_LENGTH)

        for i, alpha in enumerate(alphas):
            scatter = pg.ScatterPlotItem(
                pen=None,
                brush=pg.mkBrush(0, 255, 0, int(alpha * 255)),
                size=4 if i < self.HISTORY_LENGTH - 1 else 6
            )
            self._plot_widget.addItem(scatter)
            self._scatter_items.append(scatter)

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
        origin_alpha = float(pc.get('grid_origin_alpha', min(1.0, grid_alpha + 0.08)))
        self._name_label.setStyleSheet(f"color: {c['accent_secondary']};")
        self._info_label.setStyleSheet(f"color: {c['text_secondary']};")
        self._stats_label.setStyleSheet(f"color: {c['accent_primary']};")
        self._plot_widget.setBackground(pc['bg'])
        self._plot_widget.showGrid(x=True, y=True, alpha=grid_alpha)
        axis_pen = pg.mkPen(color=pc['axis'], width=1)
        for ax in ('left', 'bottom'):
            self._plot_widget.getAxis(ax).setPen(axis_pen)
            self._plot_widget.getAxis(ax).setTextPen(axis_pen)
        origin_color = QColor(pc['grid_major'])
        origin_color.setAlphaF(origin_alpha)
        grid_pen = pg.mkPen(color=origin_color, width=1)
        self._origin_x.setPen(grid_pen)
        self._origin_y.setPen(grid_pen)
        # Update scatter brushes with success color
        from PyQt6.QtGui import QColor as _QC
        sc = _QC(c['success'])
        r, g, b, _ = sc.getRgb()
        alphas = np.linspace(0.1, 1.0, self.HISTORY_LENGTH)
        for i, alpha in enumerate(alphas):
            self._scatter_items[i].setBrush(pg.mkBrush(r, g, b, int(alpha * 255)))

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

    def _on_pin_state_changed(self, axis: str, is_pinned: bool) -> None:
        """Handle axis pin state change from AxisController."""
        if self._pin_indicator:
            self._pin_indicator.update_state(axis, is_pinned)

    @property
    def axis_controller(self) -> Optional[AxisController]:
        """Access the axis controller for external use."""
        return self._axis_controller
