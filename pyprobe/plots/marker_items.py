import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QObject, QPointF, pyqtSignal
from PyQt6.QtGui import QFont, QMouseEvent
from typing import Optional, Tuple

from .marker_model import MarkerShape, MarkerData, MarkerType, MarkerStore

_SHAPE_MAP = {
    MarkerShape.DIAMOND: 'd',
    MarkerShape.TRIANGLE_UP: 't',
    MarkerShape.SQUARE: 's',
    MarkerShape.CROSS: '+',
    MarkerShape.CIRCLE: 'o',
    MarkerShape.STAR: 'star'
}

class _DraggableScatter(pg.ScatterPlotItem):
    """ScatterPlotItem that forwards drag events to the parent MarkerGlyph."""
    
    def __init__(self, glyph, **kwargs):
        super().__init__(**kwargs)
        self._glyph = glyph
    
    def mouseDragEvent(self, ev):
        if ev.button() != Qt.MouseButton.LeftButton:
            ev.ignore()
            return
        ev.accept()
        if ev.isFinish():
            # Final position — emit the committed move
            pos = ev.pos()
            self._glyph._on_drag_finish(pos)
        else:
            # Live dragging — update visual position
            pos = ev.pos()
            self._glyph._on_drag_move(pos)


class MarkerGlyphSignaler(QObject):
    """QObject that emits signals on behalf of MarkerGlyph (which is not a QObject)."""
    # Emitted continuously during drag: (marker_id, raw_x, raw_y)
    marker_moving = pyqtSignal(str, float, float)
    # Emitted when drag finishes: (marker_id, new_x, new_y)
    marker_moved = pyqtSignal(str, float, float)


class MarkerGlyph(pg.ItemGroup):
    """Visual representation of a single marker on the plot."""
    def __init__(self, data: MarkerData):
        super().__init__()
        self.setZValue(100)  # Always on top
        
        self.data = data
        self.signaler = MarkerGlyphSignaler()
        
        self.scatter = _DraggableScatter(self)
        self.addItem(self.scatter)
        
        # Text anchor at top-left of the point (with a slight offset to avoid covering the glyph)
        self.text = pg.TextItem(anchor=(-0.1, 1.1))
        self.addItem(self.text)
        
        self.update_glyph(data)
        
    def update_glyph(self, data: MarkerData):
        self.data = data
        symbol = _SHAPE_MAP.get(data.shape, 'd')
        color = data.color
        
        # Draw the glyph
        self.scatter.setData([data.x], [data.y], symbol=symbol, size=12, brush=pg.mkBrush(color), pen='w')
        
        # Update text
        self.text.setText(data.label)
        self.text.setColor(color)
        self.text.setPos(data.x, data.y)

    def set_visual_pos(self, x: float, y: float):
        """Update the visual position without committing to the store."""
        self.scatter.setData([x], [y],
                             symbol=_SHAPE_MAP.get(self.data.shape, 'd'),
                             size=12,
                             brush=pg.mkBrush(self.data.color),
                             pen='w')
        self.text.setPos(x, y)

    def _on_drag_move(self, pos):
        """Live visual update during drag — move glyph to the dragged position."""
        # pos is in scatter's local coords which map to data coords
        x, y = float(pos.x()), float(pos.y())
        self.set_visual_pos(x, y)
        self.signaler.marker_moving.emit(self.data.id, x, y)

    def _on_drag_finish(self, pos):
        """Emit marker_moved signal when drag finishes."""
        x, y = float(pos.x()), float(pos.y())
        self.signaler.marker_moved.emit(self.data.id, x, y)


class MarkerOverlay(QWidget):
    """
    Overlay widget in the top-right corner to display marker readouts.
    """
    marker_removed_requested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        self._overlay_layout = QVBoxLayout(self)
        self._overlay_layout.setContentsMargins(4, 4, 4, 4)
        self._overlay_layout.setSpacing(2)
        self.labels = {}
        
        from ..gui.theme.theme_manager import ThemeManager
        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.current)
        
        self.hide()
        
    def _apply_theme(self, theme):
        c = theme.colors
        bg = c['bg_dark']
        border = c['border_default']
        # Add E6 to hex for 90% opacity if it's a 7-char hex
        bg_rgba = f"{bg}E6" if len(bg) == 7 else bg
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_rgba};
                border: 1px solid {border};
                border-radius: 4px;
            }}
            QLabel {{
                color: {c['text_primary']};
                background: transparent;
                border: none;
            }}
        """)

    def update_markers(self, store: MarkerStore):
        markers = store.get_markers()
        
        if not markers:
            self.hide()
            return
        
        self.show()
        
        existing_ids = set(self.labels.keys())
        current_ids = {m.id for m in markers}
        
        for m_id in existing_ids - current_ids:
            lbl = self.labels.pop(m_id)
            self._overlay_layout.removeWidget(lbl)
            lbl.deleteLater()
            
        # Parse integers to sort
        def sort_key(x):
            try:
                return int(x.id[1:])
            except ValueError:
                return 999

        for m in sorted(markers, key=sort_key):
            dx, dy = store.get_display_values(m.id)
            
            x_str = pg.siFormat(dx, suffix='')
            y_str = pg.siFormat(dy, suffix='')
            
            if m.marker_type == MarkerType.RELATIVE and m.ref_marker_id:
                text = f"Δ{m.id}→{m.ref_marker_id}: ΔX={x_str}  ΔY={y_str}"
            else:
                text = f"{m.id}: X={x_str}  Y={y_str}"
                
            if m.id not in self.labels:
                lbl = QLabel(text)
                lbl.setObjectName(m.id)
                lbl.setFont(QFont("JetBrains Mono", 10))
                # Add a tooltip to indicate functionality
                lbl.setToolTip(f"Alt+Click to remove {m.id}")
                lbl.setStyleSheet(f"color: {m.color}; background: transparent;")
                
                self._overlay_layout.addWidget(lbl)
                self.labels[m.id] = lbl
            else:
                lbl = self.labels[m.id]
                lbl.setText(text)
                lbl.setStyleSheet(f"color: {m.color}; background: transparent;")
                
        self._reposition()

    def _reposition(self):
        """Resize to fit content and anchor to the top-right of the parent widget."""
        self.setMinimumWidth(0)
        self._overlay_layout.activate()
        self.adjustSize()
        parent = self.parentWidget()
        if parent:
            self.move(parent.width() - self.width() - 10, 10)
        self.raise_()

    def mousePressEvent(self, ev: QMouseEvent):
        if ev.modifiers() == Qt.KeyboardModifier.AltModifier:
            child = self.childAt(ev.pos())
            if isinstance(child, QLabel):
                self.marker_removed_requested.emit(child.objectName())
                ev.accept()
                return
        super().mousePressEvent(ev)


def snap_to_nearest(plot_widget, curves: dict, scene_pos: QPointF,
                    curve_viewboxes: dict | None = None) -> Tuple[Optional[str], float, float]:
    """
    Finds the nearest point on any curve to the given scene coordinates.
    Returns (trace_key, x, y) or (None, 0.0, 0.0) if snapping failed.

    curve_viewboxes: optional dict mapping trace keys to their ViewBox.
        When a curve lives in a secondary ViewBox (e.g. Phase on the right axis),
        pass {key: viewbox} so the Y-coordinate mapping uses the correct ViewBox.
        Keys not present fall back to the primary ViewBox (plotItem.vb).
    """
    primary_vb = plot_widget.plotItem.vb

    best_point = None
    best_trace_key = None
    best_y_dist = float('inf')

    for key, curve in curves.items():
        if not curve.isVisible():
            continue

        try:
            x_data, y_data = curve.getData()
            if x_data is None or len(x_data) == 0:
                continue
        except AttributeError:
            continue

        # Use the curve-specific ViewBox for coordinate mapping if provided
        vb = (curve_viewboxes or {}).get(key, primary_vb)
        view_pos = vb.mapSceneToView(scene_pos)
        vx, vy = view_pos.x(), view_pos.y()

        idx = np.argmin(np.abs(x_data - vx))
        closest_x = x_data[idx]
        closest_y = y_data[idx]

        y_dist = abs(closest_y - vy)

        if best_point is None or y_dist < best_y_dist:
            best_y_dist = y_dist
            best_point = (closest_x, closest_y)
            best_trace_key = key

    if best_point:
        return best_trace_key, float(best_point[0]), float(best_point[1])
    return None, 0.0, 0.0
