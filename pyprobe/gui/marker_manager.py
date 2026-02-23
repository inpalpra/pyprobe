from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QPushButton, QComboBox, QLineEdit,
                             QDoubleSpinBox, QLabel, QHeaderView, QColorDialog)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from ..plots.marker_model import MarkerStore, MarkerType, MarkerShape


def _store_label(store: MarkerStore) -> str:
    """Extract a human-readable label from a store's parent plot widget."""
    parent = store.parent()
    if parent and hasattr(parent, '_var_name'):
        return parent._var_name
    return "?"


class MarkerManager(QDialog):
    """Floating dialog to manage markers across all graphs."""

    _instance = None

    @classmethod
    def show_instance(cls, parent=None):
        """Show the singleton marker manager, creating it if needed."""
        if cls._instance is not None:
            try:
                cls._instance.objectName()  # check if alive
                if cls._instance.isVisible():
                    cls._instance.raise_()
                    cls._instance.activateWindow()
                    cls._instance._populate_table()
                    return cls._instance
                cls._instance.deleteLater()
            except RuntimeError:
                pass
        cls._instance = cls(parent)
        cls._instance.show()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowFlag(Qt.WindowType.Tool)
        self.setWindowTitle("Marker Manager")
        self.resize(850, 300)

        self._layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels([
            "Graph", "ID", "Label", "X", "Y", "Trace", "Type", "Ref", "Shape", "Color", "Delete"
        ])
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            header.setStretchLastSection(True)

        self._layout.addWidget(self.table)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(QLabel("Graph:"))
        self._graph_combo = QComboBox()
        self._graph_combo.setMinimumWidth(100)
        bottom_layout.addWidget(self._graph_combo)
        self.add_btn = QPushButton("Add Marker")
        self.add_btn.clicked.connect(self._on_add_clicked)
        bottom_layout.addWidget(self.add_btn)
        bottom_layout.addStretch()

        self._layout.addLayout(bottom_layout)

        from .theme.theme_manager import ThemeManager
        c = ThemeManager.instance().current.colors
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c['bg_dark']};
                color: {c['text_primary']};
            }}
            QTableWidget {{
                background-color: {c['bg_dark']};
                color: {c['text_primary']};
                gridline-color: {c['border_default']};
                border: 1px solid {c['border_default']};
            }}
            QHeaderView::section {{
                background-color: {c['bg_medium']};
                color: {c['text_secondary']};
                border: 1px solid {c['border_default']};
                padding: 4px;
            }}
        """)

        self._populating = False
        self._self_updating = False
        self._rebuild_pending = False
        self._connected_stores: list[MarkerStore] = []

        # Connect to store lifecycle signals
        MarkerStore.store_signals().stores_changed.connect(self._on_stores_changed)

        self._sync_store_connections()
        self._populate_table()

    def _on_stores_changed(self):
        """A store was added or removed — reconnect and rebuild."""
        self._sync_store_connections()
        self._schedule_rebuild()

    def _sync_store_connections(self):
        """Connect to markers_changed on all current stores, disconnect old ones."""
        # Disconnect from previously connected stores
        for store in self._connected_stores:
            try:
                store.markers_changed.disconnect(self._schedule_rebuild)
            except (TypeError, RuntimeError):
                pass

        # Connect to all current stores
        self._connected_stores = list(MarkerStore.all_stores())
        for store in self._connected_stores:
            store.markers_changed.connect(self._schedule_rebuild)

    def _on_add_clicked(self):
        idx = self._graph_combo.currentIndex()
        if idx < 0:
            return
        store = self._graph_combo.itemData(idx)
        if store is None:
            return

        plot_widget = store.parent()

        # Default trace key
        trace_key = 0
        if plot_widget and hasattr(plot_widget, 'series_keys'):
            keys = plot_widget.series_keys
            if len(keys) > 0:
                trace_key = keys[0]

        # Get center of view
        x_center = 0.0
        y_center = 0.0
        if plot_widget and hasattr(plot_widget, '_plot_widget'):
            vb = plot_widget._plot_widget.getPlotItem().getViewBox()
            xr, yr = vb.viewRange()
            x_center = sum(xr) / 2
            y_center = sum(yr) / 2

        store.add_marker(trace_key, x_center, y_center)

    def _schedule_rebuild(self):
        """Defer table rebuild to avoid destroying widgets mid-edit callback."""
        if self._self_updating:
            return
        if not self._rebuild_pending:
            self._rebuild_pending = True
            QTimer.singleShot(0, self._deferred_rebuild)

    def _deferred_rebuild(self):
        self._rebuild_pending = False
        self._populate_table()

    def _populate_table(self):
        self._populating = True
        self.table.setRowCount(0)

        stores = MarkerStore.all_stores()

        # Update graph combo
        self._graph_combo.blockSignals(True)
        prev_store = self._graph_combo.currentData()
        self._graph_combo.clear()
        for store in stores:
            label = _store_label(store)
            self._graph_combo.addItem(label, store)
        # Restore previous selection if still present
        for i in range(self._graph_combo.count()):
            if self._graph_combo.itemData(i) is prev_store:
                self._graph_combo.setCurrentIndex(i)
                break
        self._graph_combo.blockSignals(False)

        # Collect all markers with their store
        all_rows = []  # list of (store, marker, label)
        for store in stores:
            label = _store_label(store)
            for m in store.get_markers():
                all_rows.append((store, m, label))

        # Sort by marker id
        def safe_sort_key(row):
            try:
                return int(row[1].id[1:])
            except ValueError:
                return 999
        all_rows.sort(key=safe_sort_key)

        for i, (store, m, graph_label) in enumerate(all_rows):
            self.table.insertRow(i)

            # Graph (read-only)
            graph_lbl = QLabel(f" {graph_label} ")
            self.table.setCellWidget(i, 0, graph_lbl)

            # ID (read-only)
            id_lbl = QLabel(f" {m.id} ")
            self.table.setCellWidget(i, 1, id_lbl)

            # Label
            label_edit = QLineEdit(m.label)
            label_edit.textChanged.connect(lambda text, s=store, mid=m.id: self._update_marker(s, mid, label=text))
            self.table.setCellWidget(i, 2, label_edit)

            # X
            x_spin = QDoubleSpinBox()
            x_spin.setRange(-1e15, 1e15)
            x_spin.setDecimals(6)
            x_spin.setValue(m.x)
            x_spin.setKeyboardTracking(False)
            x_spin.valueChanged.connect(lambda val, s=store, mid=m.id: self._update_marker(s, mid, x=val))
            self.table.setCellWidget(i, 3, x_spin)

            # Y (read-only)
            import pyqtgraph as pg
            y_str = pg.siFormat(m.y, suffix='')
            y_lbl = QLabel(f" {y_str} ")
            self.table.setCellWidget(i, 4, y_lbl)

            # Trace
            plot_widget = store.parent()
            keys = []
            if plot_widget and hasattr(plot_widget, 'series_keys'):
                keys = plot_widget.series_keys
            elif plot_widget and hasattr(plot_widget, '_curves'):
                keys = list(range(len(plot_widget._curves)))
            if not keys:
                keys = [0]

            trace_box = QComboBox()
            for k in keys:
                trace_box.addItem(str(k), k)
            idx = trace_box.findData(m.trace_key)
            if idx >= 0:
                trace_box.setCurrentIndex(idx)
            trace_box.currentIndexChanged.connect(lambda idx, s=store, mid=m.id, tb=trace_box: self._update_marker(s, mid, trace_key=tb.itemData(idx)))
            self.table.setCellWidget(i, 5, trace_box)

            # Type
            type_box = QComboBox()
            for t in MarkerType:
                type_box.addItem(t.name, t)
            type_box.setCurrentIndex(list(MarkerType).index(m.marker_type))
            type_box.currentIndexChanged.connect(lambda idx, s=store, mid=m.id, tb=type_box: self._update_marker(s, mid, marker_type=tb.itemData(idx)))
            self.table.setCellWidget(i, 6, type_box)

            # Ref — only show markers from the same store
            same_store_markers = [row for row in all_rows if row[0] is store]
            ref_box = QComboBox()
            ref_box.addItem("None", None)
            for _, other_m, _ in same_store_markers:
                if other_m.id != m.id:
                    ref_box.addItem(other_m.id, other_m.id)
            if m.ref_marker_id:
                idx = ref_box.findData(m.ref_marker_id)
                if idx >= 0:
                    ref_box.setCurrentIndex(idx)
            ref_box.setEnabled(m.marker_type == MarkerType.RELATIVE)
            ref_box.currentIndexChanged.connect(lambda idx, s=store, mid=m.id, rb=ref_box: self._update_marker(s, mid, ref_marker_id=rb.itemData(idx)))
            self.table.setCellWidget(i, 7, ref_box)

            # Shape
            shape_box = QComboBox()
            for sh in MarkerShape:
                shape_box.addItem(sh.name, sh)
            shape_box.setCurrentIndex(list(MarkerShape).index(m.shape))
            shape_box.currentIndexChanged.connect(lambda idx, s=store, mid=m.id, sb=shape_box: self._update_marker(s, mid, shape=sb.itemData(idx)))
            self.table.setCellWidget(i, 8, shape_box)

            # Color
            col_btn = QPushButton("Color")
            col_btn.setStyleSheet(f"background-color: {m.color}; color: {'#000' if QColor(m.color).lightness() > 128 else '#fff'};")
            col_btn.clicked.connect(lambda _, s=store, mid=m.id, c=m.color: self._pick_color(s, mid, c))
            self.table.setCellWidget(i, 9, col_btn)

            # Delete
            del_btn = QPushButton("\u2715")
            del_btn.setMaximumWidth(40)
            del_btn.clicked.connect(lambda _, s=store, mid=m.id: s.remove_marker(mid))
            self.table.setCellWidget(i, 10, del_btn)

        self._populating = False

    def _update_marker(self, store, marker_id, **kwargs):
        if not self._populating:
            self._self_updating = True
            store.update_marker(marker_id, **kwargs)
            self._self_updating = False

    def _pick_color(self, store, marker_id, current_color):
        color = QColorDialog.getColor(QColor(current_color), self, "Pick Marker Color")
        if color.isValid():
            store.update_marker(marker_id, color=color.name())
