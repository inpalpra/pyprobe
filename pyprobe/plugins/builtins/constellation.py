"""Constellation diagram plugin for complex arrays."""
from typing import Any, Optional, Tuple, List
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import QRectF, QTimer, Qt, pyqtSignal

from ..base import ProbePlugin
from ...core.data_classifier import DTYPE_ARRAY_COMPLEX, DTYPE_WAVEFORM_COMPLEX
from ...plots.axis_controller import AxisController
from ...plots.pin_indicator import PinIndicator
from ...plots.editable_axis import EditableAxisItem
from ...gui.axis_editor import AxisEditor
from ...plots.marker_model import MarkerStore
from ...plots.marker_items import MarkerOverlay, MarkerGlyph, snap_to_nearest

class ConstellationWidget(QWidget):
    """Scatter plot widget for I/Q data."""

    status_message_requested = pyqtSignal(str)
    
    MAX_DISPLAY_POINTS = 10000
    HISTORY_LENGTH = 5  # Number of frames to show with fading
    
    def __init__(self, var_name: str, color: QColor, parent: Optional[QWidget] = None, trace_id: str = ""):
        super().__init__(parent)
        self._var_name = var_name
        self._color = color
        self._trace_id = trace_id
        self._data: Optional[np.ndarray] = None
        self._history: List[np.ndarray] = []
        
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
        header.addWidget(self._info_label)
        layout.addLayout(header)

        # PyQtGraph plot widget
        self._plot_widget = pg.PlotWidget()
        self._configure_plot()
        layout.addWidget(self._plot_widget)

        # M2.5: Add legend by default
        from pyprobe.gui.probe_panel import RemovableLegendItem
        from pyprobe.gui.theme.theme_manager import ThemeManager
        theme_colors = ThemeManager.instance().current.colors
        self._legend = RemovableLegendItem(
            offset=(10, 10),
            labelTextColor=theme_colors.get('text_primary', '#ffffff'),
            brush=pg.mkBrush(theme_colors.get('bg_medium', '#1a1a1a') + '80')
        )
        self._legend.setParentItem(self._plot_widget.getPlotItem())
        # Add primary signal to legend if we have scatter items
        if self._scatter_items:
            label = f"{self._trace_id}: {self._var_name}" if self._trace_id else self._var_name
            self._legend.addItem(self._scatter_items[-1], label)

        # Stats bar
        self._stats_label = QLabel("Power: -- dB | Symbols: --")
        self._stats_label.setFont(QFont("JetBrains Mono", 9))
        self._stats_label.setStyleSheet(f"color: {self._color.name()};")
        layout.addWidget(self._stats_label)

        # Footer spacer to make room for the hover toolbar
        self._footer_spacer = QLabel("")
        self._footer_spacer.setFixedHeight(24)
        layout.addWidget(self._footer_spacer)
    
    def _configure_plot(self):
        """Configure the constellation plot appearance."""
        self._plot_widget.setBackground('#0d0d0d')
        # Use a more visible default grid alpha (0.6) before theme override
        self._plot_widget.showGrid(x=True, y=True, alpha=0.6)
        self._plot_widget.useOpenGL(False)
        self._plot_widget.setAspectLocked(True)

        # Setup editable axes
        self._setup_editable_axes()
        
        # Add labels AFTER replacing axes
        self._plot_widget.setLabel('left', 'Q (Imag)')
        self._plot_widget.setLabel('bottom', 'I (Real)')
        
        # Axis editor (inline text editor)
        self._axis_editor = AxisEditor(self._plot_widget)
        self._axis_editor.value_committed.connect(self._on_axis_value_committed)
        self._axis_editor.editing_cancelled.connect(self._on_axis_edit_cancelled)

        # Add cross-hair at origin
        self._origin_x = self._plot_widget.addLine(x=0, pen=pg.mkPen('#333333', width=1))
        self._origin_y = self._plot_widget.addLine(y=0, pen=pg.mkPen('#333333', width=1))
        
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

        # Setup axis controller and pin indicator
        plot_item = self._plot_widget.getPlotItem()
        self._axis_controller = AxisController(plot_item)
        self._axis_controller.pin_state_changed.connect(self._on_pin_state_changed)

        self._pin_indicator = PinIndicator(self)
        self._pin_indicator.x_pin_clicked.connect(lambda: self._axis_controller.toggle_pin('x'))
        self._pin_indicator.y_pin_clicked.connect(lambda: self._axis_controller.toggle_pin('y'))
        self._pin_indicator.raise_()
        self._pin_indicator.show()

        # Mouse hover coordinate display
        self._plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)
        
        # M3: Marker System
        self._marker_store = MarkerStore(self)
        self._marker_overlay = MarkerOverlay(self._plot_widget)
        self._marker_store.markers_changed.connect(self._refresh_markers)
        self._marker_overlay.marker_removed_requested.connect(self._marker_store.remove_marker)
        self._marker_glyphs = {}
        
        self._plot_widget.scene().sigMouseClicked.connect(self._on_mouse_clicked)

    def _apply_theme(self, theme) -> None:
        c = theme.colors
        pc = theme.plot_colors
        grid_alpha = float(pc.get('grid_alpha', 0.28))
        origin_alpha = float(pc.get('grid_origin_alpha', min(1.0, grid_alpha + 0.08)))
        self._info_label.setStyleSheet(f"color: {c['text_secondary']};")
        self._plot_widget.setBackground(pc['bg'])
        self._plot_widget.showGrid(x=True, y=True, alpha=grid_alpha)
        
        # Color axis labels
        label_style = {'color': c['text_secondary'], 'font-size': '10pt'}
        self._plot_widget.setLabel('left', 'Q (Imag)', **label_style)
        self._plot_widget.setLabel('bottom', 'I (Real)', **label_style)
        
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
        
        origin_color = QColor(pc['grid_major'])
        origin_color.setAlphaF(origin_alpha)
        grid_pen = pg.mkPen(color=origin_color, width=1)
        self._origin_x.setPen(grid_pen)
        self._origin_y.setPen(grid_pen)

    def downsample(self, data: np.ndarray) -> np.ndarray:
        """Randomly subsample for display."""
        if len(data) <= self.MAX_DISPLAY_POINTS:
            return data
        indices = np.random.choice(len(data), self.MAX_DISPLAY_POINTS, replace=False)
        return data[indices]

    def set_color(self, color: QColor) -> None:
        """Update the probe color (name label, stats, scatter brushes)."""
        self._color = color
        hex_color = color.name()
        self._name_label.setStyleSheet(f"color: {hex_color};")
        self._stats_label.setStyleSheet(f"color: {hex_color};")
        # Recompute scatter brushes with new color
        r, g, b, _ = color.getRgb()
        alphas = np.linspace(0.1, 1.0, self.HISTORY_LENGTH)
        for i, (scatter, alpha) in enumerate(zip(self._scatter_items, alphas)):
            scatter.setBrush(pg.mkBrush(r, g, b, int(alpha * 255)))

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
        """Update the constellation with new complex data."""
        if value is None:
            return
        
        if not isinstance(value, np.ndarray):
            try:
                value = np.asarray(value)
            except (ValueError, TypeError):
                return
        
        self._data = value.flatten()
        
        if not np.issubdtype(self._data.dtype, np.complexfloating):
            self._data = self._data.astype(np.complex128)
            
        self._history.append(self._data.copy())
        if len(self._history) > self.HISTORY_LENGTH:
            self._history.pop(0)
            
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
                self._scatter_items[scatter_idx].setData(x=data.real, y=data.imag)
        
        # Note: Do NOT call autoRange() here - AxisController manages auto-ranging
        # via enableAutoRange(). Calling autoRange() every frame would override
        # any pinned axis settings.
            
            
        self._info_label.setText(source_info)
        self._update_stats(shape=shape if shape else value.shape)
        self._refresh_markers()

    def _update_stats(self, shape: Optional[tuple] = None):
        """Update constellation statistics."""
        if self._data is None or len(self._data) == 0:
            return
        
        power = np.mean(np.abs(self._data) ** 2)
        power_db = 10 * np.log10(power) if power > 0 else -np.inf
        
        prefix = f"Shape: {shape} | " if shape else ""
        self._stats_label.setText(f"{prefix}Power: {power_db:.2f} dB | Symbols: {len(self._data)}")

    def _on_pin_state_changed(self, axis: str, is_pinned: bool) -> None:
        """Handle axis pin state change from AxisController."""
        if self._pin_indicator:
            self._pin_indicator.update_state(axis, is_pinned)
        
        # Constellation uses aspect locking for proper I/Q display, but this
        # prevents independent axis control. Unlock aspect when any axis is pinned.
        if self._axis_controller:
            any_pinned = self._axis_controller.x_pinned or self._axis_controller.y_pinned
            self._plot_widget.setAspectLocked(not any_pinned)

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
        if hasattr(self, '_marker_overlay'):
            self._marker_overlay._reposition()

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
        """Reset the view: unpin axes, re-lock aspect, snap to full range."""
        if self._axis_controller:
            self._axis_controller.set_pinned('x', False)
            self._axis_controller.set_pinned('y', False)
        # Re-lock aspect for proper I/Q display
        self._plot_widget.setAspectLocked(True)
        vb = self._plot_widget.getPlotItem().getViewBox()
        vb.autoRange(padding=0)
        self._refresh_markers()

    # ── Mouse hover coordinate helpers ─────────────────────

    def _on_mouse_moved(self, pos):
        """Format hover coordinates and emit status_message_requested."""
        from .complex_plots import format_coord
        vb = self._plot_widget.plotItem.vb
        mouse_point = vb.mapSceneToView(pos)
        x_str = format_coord(mouse_point.x())
        y_str = format_coord(mouse_point.y())
        self.status_message_requested.emit(f"X: {x_str},  Y: {y_str}")

    def leaveEvent(self, event):
        """Clear status bar when mouse leaves the plot widget."""
        super().leaveEvent(event)
        self.status_message_requested.emit("")

    def _on_mouse_clicked(self, ev):
        if ev.modifiers() == Qt.KeyboardModifier.AltModifier and ev.button() == Qt.MouseButton.LeftButton:
            ev.accept()
            curve_dict = {f"history_{i}": scatter for i, scatter in enumerate(self._scatter_items)}
            trace_key, x, y = snap_to_nearest(self._plot_widget, curve_dict, ev.scenePos())
            if trace_key is not None:
                self._marker_store.add_marker(trace_key, x, y)
                
    def _refresh_markers(self):
        plot_item = self._plot_widget.getPlotItem()
        for glyph in self._marker_glyphs.values():
            plot_item.removeItem(glyph)
        self._marker_glyphs.clear()
        
        # Mapping trace keys back to scatter items
        curve_dict = {f"history_{i}": scatter for i, scatter in enumerate(self._scatter_items)}
        
        # Block signals to avoid infinite recursion (we're called from markers_changed)
        self._marker_store.blockSignals(True)
        for m in self._marker_store.get_markers():
            if m.trace_key in curve_dict:
                curve = curve_dict[m.trace_key]
                x_data, y_data = curve.getData()
                if x_data is not None and len(x_data) > 0:
                    # Use Euclidean distance for scatter (I/Q) data
                    dist = (x_data - m.x)**2 + (y_data - m.y)**2
                    idx = np.argmin(dist)
                    new_x, new_y = float(x_data[idx]), float(y_data[idx])
                    updates = {}
                    if new_x != m.x:
                        updates['x'] = new_x
                    if new_y != m.y:
                        updates['y'] = new_y
                    if updates:
                        self._marker_store.update_marker(m.id, **updates)
            
            glyph = MarkerGlyph(m)
            glyph.signaler.marker_moved.connect(self._on_marker_dragged)
            plot_item.addItem(glyph)
            self._marker_glyphs[m.id] = glyph
        self._marker_store.blockSignals(False)
            
        self._marker_overlay.update_markers(self._marker_store)

    def _on_marker_dragged(self, marker_id: str, new_x: float, new_y: float):
        """Handle marker drag — snap to nearest constellation point and persist."""
        m = self._marker_store.get_marker(marker_id)
        if m is None:
            return

        curve_dict = {f"history_{i}": scatter for i, scatter in enumerate(self._scatter_items)}
        curve = curve_dict.get(m.trace_key)
        if curve is not None:
            x_data, y_data = curve.getData()
            if x_data is not None and len(x_data) > 0:
                dist = (x_data - new_x)**2 + (y_data - new_y)**2
                idx = np.argmin(dist)
                new_x = float(x_data[idx])
                new_y = float(y_data[idx])

        self._marker_store.update_marker(marker_id, x=new_x, y=new_y)

    def get_plot_data(self) -> dict:
        """
        Return the data currently plotted on the constellation.
        
        Returns:
            dict with 'real', 'imag' keys containing lists of values,
            'mean_real', 'mean_imag' for statistics verification,
            and 'history_count' with number of frames stored.
        """
        if self._data is None or len(self._data) == 0:
            return {
                'real': [], 'imag': [],
                'mean_real': 0.0, 'mean_imag': 0.0,
                'history_count': 0
            }
        
        return {
            'real': self._data.real.tolist(),
            'imag': self._data.imag.tolist(),
            'mean_real': float(np.mean(self._data.real)),
            'mean_imag': float(np.mean(self._data.imag)),
            'history_count': len(self._history)
        }


class ConstellationPlugin(ProbePlugin):
    """Plugin for visualizing complex arrays as constellation diagrams."""
    
    name = "Constellation"
    icon = "constellation"
    priority = 100  # High priority for complex arrays
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype in (DTYPE_ARRAY_COMPLEX, DTYPE_WAVEFORM_COMPLEX)
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None, trace_id: str = "") -> QWidget:
        return ConstellationWidget(var_name, color, parent, trace_id=trace_id)
    
    def update(self, widget: QWidget, value: Any, dtype: str,
               shape: Optional[Tuple[int, ...]] = None,
               source_info: str = "") -> None:
        if isinstance(widget, ConstellationWidget):
            # Extract complex samples from waveform if needed
            if isinstance(value, dict) and value.get('__dtype__') == DTYPE_WAVEFORM_COMPLEX:
                value = np.asarray(value['samples'])
            elif dtype == DTYPE_WAVEFORM_COMPLEX:
                # Direct waveform object — extract samples array
                from ...core.data_classifier import get_waveform_info
                waveform_info = get_waveform_info(value)
                if waveform_info is not None:
                    value = np.asarray(getattr(value, waveform_info['samples_attr']))
            widget.update_data(value, dtype, shape, source_info)
