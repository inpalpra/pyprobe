from typing import Any, Optional, Tuple, List, Dict
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QRectF, QTimer

from ..base import ProbePlugin
from ...core.data_classifier import DTYPE_ARRAY_COMPLEX
from ...plots.axis_controller import AxisController
from ...plots.pin_indicator import PinIndicator
from ...plots.draw_mode import DrawMode, apply_draw_mode

MAX_DISPLAY_POINTS = 5000

def downsample(data: np.ndarray, n_points: int = 0, x_offset: int = 0) -> tuple:
    """Downsample large data for display, returning (x_indices, y_values)."""
    if n_points <= 0:
        n_points = MAX_DISPLAY_POINTS

    if len(data) <= n_points:
        return np.arange(len(data)) + x_offset, data
    
    n_chunks = n_points // 2
    chunk_size = len(data) // n_chunks
    truncated = data[:n_chunks * chunk_size]
    reshaped = truncated.reshape(n_chunks, chunk_size)
    
    mins = reshaped.min(axis=1)
    maxs = reshaped.max(axis=1)
    
    chunk_starts = np.arange(n_chunks) * chunk_size
    x = np.empty(n_chunks * 2, dtype=np.int64)
    x[0::2] = chunk_starts + x_offset
    x[1::2] = chunk_starts + (chunk_size - 1) + x_offset
    
    y = np.empty(n_chunks * 2, dtype=data.dtype)
    y[0::2] = mins
    y[1::2] = maxs
    return x, y

class ComplexWidget(QWidget):
    """Base widget for complex time-domain plots with zoom-responsive downsampling."""
    
    def __init__(self, var_name: str, color: QColor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._var_name = var_name
        self._color = color
        self._plot_widget = pg.PlotWidget()
        self._info_label = QLabel("")
        self._raw_data: Optional[np.ndarray] = None  # Raw complex array
        
        # Axis pinning
        self._axis_controller: Optional[AxisController] = None
        self._pin_indicator: Optional[PinIndicator] = None
        
        # Per-series draw mode: series_key -> DrawMode
        self._draw_modes: Dict[str, DrawMode] = {}
        # Series key -> (curve, color_hex) for apply_draw_mode
        self._series_curves: Dict[str, tuple] = {}
        
        # Zoom-responsive state
        self._zoom_timer = QTimer()
        self._zoom_timer.setSingleShot(True)
        self._zoom_timer.setInterval(50)
        self._zoom_timer.timeout.connect(self._rerender_for_zoom)
        self._updating_curves = False
        
        self._setup_ui()
        self._configure_plot()

        from ...gui.theme.theme_manager import ThemeManager
        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.current)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        header = QHBoxLayout()
        name_label = QLabel(self._var_name)
        name_label.setFont(QFont("JetBrains Mono", 11, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {self._color.name()};")
        header.addWidget(name_label)
        header.addStretch()
        
        self._info_label.setFont(QFont("JetBrains Mono", 9))
        self._info_label.setStyleSheet("color: #888888;")
        header.addWidget(self._info_label)
        layout.addLayout(header)
        
        layout.addWidget(self._plot_widget)

    def _configure_plot(self):
        self._plot_widget.setBackground('#0d0d0d')
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.setLabel('bottom', 'Sample Index')
        self._plot_legend = self._plot_widget.addLegend(offset=(10, 10))
        
        # Setup axis controller and pin indicator
        plot_item = self._plot_widget.getPlotItem()
        self._axis_controller = AxisController(plot_item)
        self._axis_controller.pin_state_changed.connect(self._on_pin_state_changed)

        self._pin_indicator = PinIndicator(self)
        self._pin_indicator.x_pin_clicked.connect(lambda: self._axis_controller.toggle_pin('x'))
        self._pin_indicator.y_pin_clicked.connect(lambda: self._axis_controller.toggle_pin('y'))
        self._pin_indicator.raise_()
        self._pin_indicator.show()

        # Zoom-responsive: connect sigRangeChanged
        vb = plot_item.getViewBox()
        vb.sigRangeChanged.connect(self._on_view_range_changed)

    def _apply_theme(self, theme) -> None:
        c = theme.colors
        pc = theme.plot_colors
        grid_alpha = float(pc.get('grid_alpha', 0.28))
        self._plot_widget.setBackground(pc['bg'])
        self._plot_widget.showGrid(x=True, y=True, alpha=grid_alpha)
        self._info_label.setStyleSheet(f"color: {c['text_secondary']};")

    def update_info(self, text: str):
        self._info_label.setText(text)

    def _register_series(self, key: str, curve, color_hex: str) -> None:
        """Register a named series for draw mode control."""
        self._draw_modes[key] = DrawMode.LINE
        self._series_curves[key] = (curve, color_hex)

    def set_draw_mode(self, series_key: str, mode: DrawMode) -> None:
        """Set the draw mode for a named series."""
        if series_key not in self._series_curves:
            return
        self._draw_modes[series_key] = mode
        curve, color_hex = self._series_curves[series_key]
        apply_draw_mode(curve, mode, color_hex)

    def get_draw_mode(self, series_key: str) -> DrawMode:
        """Get the current draw mode for a named series."""
        return self._draw_modes.get(series_key, DrawMode.LINE)

    @property
    def series_keys(self) -> list:
        """Return the list of registered series keys."""
        return list(self._draw_modes.keys())

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

    # ── Zoom-responsive downsampling ──────────────────────

    def _on_view_range_changed(self, vb, ranges):
        """Handle view range changes — debounce and re-render."""
        if self._updating_curves or self._raw_data is None:
            return
        self._zoom_timer.start()

    def _rerender_for_zoom(self):
        """Re-downsample or show raw data based on visible x-range.

        Subclasses implement _render_slice(i_min, i_max) which produces
        the derived arrays (real, imag, mag, phase, etc.) for the visible
        slice, then calls setData on their curves.
        """
        if self._raw_data is None:
            return
        vb = self._plot_widget.getPlotItem().getViewBox()
        x_min, x_max = vb.viewRange()[0]
        n = len(self._raw_data)
        i_min = max(0, int(np.floor(x_min)))
        i_max = min(n, int(np.ceil(x_max)) + 1)
        if i_min >= i_max:
            return
        self._updating_curves = True
        self._render_slice(i_min, i_max)
        self._updating_curves = False

    def _render_slice(self, i_min: int, i_max: int):
        """Override in subclasses to re-render the visible slice."""
        pass

    def reset_view(self) -> None:
        """Reset the view: restore full data to curves, unpin axes, snap to full range."""
        if self._raw_data is None:
            return
        # Restore full dataset to curves via subclass _render_slice
        n = len(self._raw_data)
        self._updating_curves = True
        self._render_slice(0, n)
        self._updating_curves = False
        # Unpin axes and snap to full range
        if self._axis_controller:
            self._axis_controller.set_pinned('x', False)
            self._axis_controller.set_pinned('y', False)
        vb = self._plot_widget.getPlotItem().getViewBox()
        vb.autoRange(padding=0)

    # ── get_plot_data for testing ────────────────────────

    def get_plot_data(self) -> list:
        """Return data currently plotted, for test verification."""
        result = []
        for key, (curve, _color) in self._series_curves.items():
            x_data, y_data = curve.getData()
            if x_data is not None and y_data is not None:
                result.append({'name': key, 'x': list(x_data), 'y': list(y_data)})
            else:
                result.append({'name': key, 'x': [], 'y': []})
        return result


class ComplexRIWidget(ComplexWidget):
    """Real & Imaginary components."""
    
    def __init__(self, var_name: str, color: QColor, parent: Optional[QWidget] = None):
        super().__init__(var_name, color, parent)
        self._real_curve = self._plot_widget.plot(pen=pg.mkPen('#00ffff', width=1.5), name="Real")
        self._imag_curve = self._plot_widget.plot(pen=pg.mkPen('#ff00ff', width=1.5), name="Imag")
        self._plot_widget.setLabel('left', 'Amplitude')
        self._register_series('Real', self._real_curve, '#00ffff')
        self._register_series('Imag', self._imag_curve, '#ff00ff')

    def update_data(self, value: np.ndarray):
        value = np.atleast_1d(value)
        self._raw_data = value

        self._updating_curves = True
        real = value.real
        imag = value.imag
        x_r, y_r = downsample(real)
        x_i, y_i = downsample(imag)
        self._real_curve.setData(x_r, y_r)
        self._imag_curve.setData(x_i, y_i)
        self._updating_curves = False
        self.update_info(f"[{value.shape}]")

    def _render_slice(self, i_min: int, i_max: int):
        """Re-render real & imag for the visible slice."""
        sliced = self._raw_data[i_min:i_max]
        real = sliced.real
        imag = sliced.imag
        x_r, y_r = downsample(real, x_offset=i_min)
        x_i, y_i = downsample(imag, x_offset=i_min)
        self._real_curve.setData(x_r, y_r)
        self._imag_curve.setData(x_i, y_i)


class ComplexMAWidget(ComplexWidget):
    """Magnitude (Log) & Phase."""
    
    def __init__(self, var_name: str, color: QColor, parent: Optional[QWidget] = None):
        super().__init__(var_name, color, parent)
        
        # Mag on left axis
        self._mag_curve = self._plot_widget.plot(pen=pg.mkPen('#ffff00', width=1.5), name="Log Mag (dB)")
        self._plot_widget.setLabel('left', 'Magnitude (dB)', color='#ffff00')
        
        self._p1 = self._plot_widget.plotItem
        self._p2 = pg.ViewBox()
        self._p1.showAxis('right')
        self._p1.scene().addItem(self._p2)
        self._p1.getAxis('right').linkToView(self._p2)
        self._p2.setXLink(self._p1)
        self._p1.getAxis('right').setLabel('Phase (rad)', color='#00ff00')
        
        self._phase_curve = pg.PlotDataItem(pen=pg.mkPen('#00ff7f', width=1.5))
        self._p2.addItem(self._phase_curve)
        
        self._plot_legend.addItem(self._mag_curve, "Log Mag")
        self._plot_legend.addItem(self._phase_curve, "Phase")
        
        self._register_series('Log Mag', self._mag_curve, '#ffff00')
        self._register_series('Phase', self._phase_curve, '#00ff7f')
        
        # Handle view resize
        self._p1.vb.sigResized.connect(self._update_views)

    def _update_views(self):
        self._p2.setGeometry(self._p1.vb.sceneBoundingRect())
        self._p2.linkedViewChanged(self._p1.vb, self._p2.XAxis)

    def _on_pin_state_changed(self, axis: str, is_pinned: bool) -> None:
        """Handle axis pin state - also control secondary Y axis for phase."""
        super()._on_pin_state_changed(axis, is_pinned)
        if axis == 'y':
            self._p2.enableAutoRange(axis='y', enable=not is_pinned)

    def update_data(self, value: np.ndarray):
        value = np.atleast_1d(value)
        self._raw_data = value

        self._updating_curves = True
        mag_db = 20 * np.log10(np.abs(value) + 1e-12)
        phase = np.angle(value)
        x_m, y_m = downsample(mag_db)
        x_p, y_p = downsample(phase)
        self._mag_curve.setData(x_m, y_m)
        self._phase_curve.setData(x_p, y_p)
        self._updating_curves = False
        self.update_info(f"[{value.shape}]")

    def _render_slice(self, i_min: int, i_max: int):
        """Re-render mag & phase for the visible slice."""
        sliced = self._raw_data[i_min:i_max]
        mag_db = 20 * np.log10(np.abs(sliced) + 1e-12)
        phase = np.angle(sliced)
        x_m, y_m = downsample(mag_db, x_offset=i_min)
        x_p, y_p = downsample(phase, x_offset=i_min)
        self._mag_curve.setData(x_m, y_m)
        self._phase_curve.setData(x_p, y_p)


class SingleCurveWidget(ComplexWidget):
    """Generic single curve complex view."""
    
    def __init__(self, var_name: str, color: QColor, title: str, parent: Optional[QWidget] = None):
        super().__init__(var_name, color, parent)
        self._title = title
        self._curve = self._plot_widget.plot(pen=pg.mkPen(color.name(), width=1.5), name=title)
        self._plot_widget.setLabel('left', title)
        self._register_series(title, self._curve, color.name())
        self._raw_real_data: Optional[np.ndarray] = None  # Pre-computed real array

    def set_data(self, data: np.ndarray, info: str):
        self._raw_real_data = data
        self._raw_data = data  # Base class zoom guard checks this
        self._updating_curves = True
        x, y = downsample(data)
        self._curve.setData(x, y)
        self._updating_curves = False
        self.update_info(info)

    def _render_slice(self, i_min: int, i_max: int):
        """Re-render for the visible slice using pre-computed real data."""
        source = self._raw_real_data if self._raw_real_data is not None else self._raw_data
        if source is None:
            return
        sliced = source[i_min:i_max]
        x, y = downsample(sliced, x_offset=i_min)
        self._curve.setData(x, y)

# --- PLUGINS ---

class ComplexRIPlugin(ProbePlugin):
    name = "Real & Imag"
    icon = "activity"
    priority = 90
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype == DTYPE_ARRAY_COMPLEX
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None) -> QWidget:
        return ComplexRIWidget(var_name, color, parent)
    
    def update(self, widget: QWidget, value: Any, dtype: str, shape=None, source_info: str = "") -> None:
        if isinstance(widget, ComplexRIWidget):
            widget.update_data(np.asanyarray(value))

class ComplexMAPlugin(ProbePlugin):
    name = "Mag & Phase"
    icon = "bar-chart-2"
    priority = 85
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype == DTYPE_ARRAY_COMPLEX
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None) -> QWidget:
        return ComplexMAWidget(var_name, color, parent)
    
    def update(self, widget: QWidget, value: Any, dtype: str, shape=None, source_info: str = "") -> None:
        if isinstance(widget, ComplexMAWidget):
            widget.update_data(np.asanyarray(value))

class LogMagPlugin(ProbePlugin):
    name = "Log Mag (dB)"
    icon = "activity"
    priority = 80
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype == DTYPE_ARRAY_COMPLEX
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None) -> QWidget:
        return SingleCurveWidget(var_name, color, "Magnitude (dB)", parent)
    
    def update(self, widget: QWidget, value: Any, dtype: str, shape=None, source_info: str = "") -> None:
        if isinstance(widget, SingleCurveWidget):
            val = np.asanyarray(value)
            mag_db = 20 * np.log10(np.abs(val) + 1e-12)
            widget.set_data(mag_db, f"[{val.shape}]")

class LinearMagPlugin(ProbePlugin):
    name = "Linear Mag"
    icon = "activity"
    priority = 75
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype == DTYPE_ARRAY_COMPLEX
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None) -> QWidget:
        return SingleCurveWidget(var_name, color, "Magnitude", parent)
    
    def update(self, widget: QWidget, value: Any, dtype: str, shape=None, source_info: str = "") -> None:
        if isinstance(widget, SingleCurveWidget):
            val = np.asanyarray(value)
            widget.set_data(np.abs(val), f"[{val.shape}]")

class PhaseRadPlugin(ProbePlugin):
    name = "Phase (rad)"
    icon = "activity"
    priority = 70
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype == DTYPE_ARRAY_COMPLEX
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None) -> QWidget:
        return SingleCurveWidget(var_name, color, "Phase (rad)", parent)
    
    def update(self, widget: QWidget, value: Any, dtype: str, shape=None, source_info: str = "") -> None:
        if isinstance(widget, SingleCurveWidget):
            val = np.asanyarray(value)
            widget.set_data(np.angle(val), f"[{val.shape}]")

class PhaseDegPlugin(ProbePlugin):
    name = "Phase (deg)"
    icon = "activity"
    priority = 65
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype == DTYPE_ARRAY_COMPLEX
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None) -> QWidget:
        return SingleCurveWidget(var_name, color, "Phase (deg)", parent)
    
    def update(self, widget: QWidget, value: Any, dtype: str, shape=None, source_info: str = "") -> None:
        if isinstance(widget, SingleCurveWidget):
            val = np.asanyarray(value)
            deg = np.rad2deg(np.angle(val))
            widget.set_data(deg, f"[{val.shape}]")
