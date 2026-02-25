from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QPushButton, QComboBox, QLineEdit, QWidget,
                             QDoubleSpinBox, QLabel, QHeaderView, QColorDialog, QCheckBox,
                             QStyledItemDelegate)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QColor

from ..plots.marker_model import MarkerStore, MarkerType, MarkerShape


class ItemHeightDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(24)
        return size


class TypeToggleWidget(QWidget):
    """A segmented toggle for Absolute/Relative marker types."""
    
    typeChanged = pyqtSignal(object) # MarkerType

    def __init__(self, current_type: MarkerType, parent=None):
        super().__init__(parent)
        self._type = current_type
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.abs_btn = QPushButton("Abs")
        self.abs_btn.setCheckable(True)
        self.abs_btn.setFixedSize(32, 20)
        
        self.rel_btn = QPushButton("Rel")
        self.rel_btn.setCheckable(True)
        self.rel_btn.setFixedSize(32, 20)
        
        layout.addWidget(self.abs_btn)
        layout.addWidget(self.rel_btn)
        
        self.abs_btn.clicked.connect(lambda: self._set_type(MarkerType.ABSOLUTE))
        self.rel_btn.clicked.connect(lambda: self._set_type(MarkerType.RELATIVE))
        
        self._update_styles()

    def _set_type(self, marker_type: MarkerType):
        if self._type != marker_type:
            self._type = marker_type
            self._update_styles()
            self.typeChanged.emit(marker_type)
        else:
            # Re-ensure correct state if clicked while already active
            self._update_styles()

    def setType(self, marker_type: MarkerType):
        if self._type != marker_type:
            self._type = marker_type
            self._update_styles()

    def _update_styles(self):
        from .theme.theme_manager import ThemeManager
        c = ThemeManager.instance().current.colors
        
        active_style = f"""
            QPushButton {{
                background-color: {c['bg_light']};
                color: {c['text_primary']};
                font-size: 10px;
                font-weight: bold;
                border: 1px solid {c['border_default']};
                border-radius: 2px;
            }}
        """
        inactive_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {c['text_secondary']};
                font-size: 10px;
                border: 1px solid transparent;
                border-radius: 2px;
            }}
            QPushButton:hover {{
                background-color: {c['bg_medium']};
            }}
        """
        
        self.abs_btn.setChecked(self._type == MarkerType.ABSOLUTE)
        self.rel_btn.setChecked(self._type == MarkerType.RELATIVE)
        
        self.abs_btn.setStyleSheet(active_style if self._type == MarkerType.ABSOLUTE else inactive_style)
        self.rel_btn.setStyleSheet(active_style if self._type == MarkerType.RELATIVE else inactive_style)


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
        
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)

        self._layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 11)
        self.table.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.table.setHorizontalHeaderLabels([
            "Graph", "ID", "Label", "X", "Y", "Trace", "Type", "Ref", "Shape", "Color", "Delete"
        ])
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            header.setStretchLastSection(True)

        self._layout.addWidget(self.table)

        bottom_layout = QHBoxLayout()
        self.detailed_chk = QCheckBox("Detailed View")
        self.detailed_chk.setChecked(False)
        self.detailed_chk.stateChanged.connect(self._toggle_columns)
        bottom_layout.addWidget(self.detailed_chk)
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
                border: none;
                alternate-background-color: {c['bg_medium']};
                selection-background-color: {c['bg_light']};
                selection-color: {c['text_primary']};
            }}
            QTableWidget::item:selected {{
                background-color: {c['bg_light']};
                color: {c['text_primary']};
            }}
            QHeaderView::section {{
                background-color: {c['bg_dark']};
                color: {c['text_secondary']};
                border: none;
                border-bottom: 1px solid {c['border_default']};
                padding: 4px;
                font-weight: bold;
            }}
            QLineEdit, QComboBox, QDoubleSpinBox, QPushButton, QCheckBox {{
                background: transparent;
                border: none;
                color: {c['text_primary']};
                padding: 2px;
                margin: 0px;
                text-align: center;
            }}
            QComboBox QAbstractItemView {{
                background-color: {c['bg_medium']};
                color: {c['text_primary']};
                border: 1px solid {c['border_default']};
                selection-background-color: {c['accent_primary'] if 'accent_primary' in c else c['bg_light']};
                selection-color: {c['bg_dark'] if 'accent_primary' in c else c['text_primary']};
                min-height: 100px;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 24px;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {c['accent_primary'] if 'accent_primary' in c else c['bg_light']};
                color: {c['bg_darkest'] if 'bg_darkest' in c else c['bg_dark']};
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {c['accent_primary'] if 'accent_primary' in c else c['bg_light']};
                color: {c['bg_darkest'] if 'bg_darkest' in c else c['bg_dark']};
            }}
            QComboBox::drop-down, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                border: none;
                background: transparent;
            }}
            QPushButton {{
                background-color: {c['bg_medium']};
                border-radius: 2px;
            }}
            QPushButton:hover {{
                background-color: {c['border_default']};
            }}
        """)

        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        self._populating = False
        self._self_updating = False
        self._rebuild_pending = False
        self._current_row_markers = []
        self._connected_stores: list[MarkerStore] = []
        self._combo_delegate = ItemHeightDelegate(self)

        # Connect to store lifecycle signals
        MarkerStore.store_signals().stores_changed.connect(self._on_stores_changed)

        self._sync_store_connections()
        self._populate_table()
        self._toggle_columns()

    def _toggle_columns(self):
        detailed = self.detailed_chk.isChecked()
        # In basic view, only keep ID (1), X (3), and Y (4)
        self.table.setColumnHidden(0, not detailed) # Graph
        self.table.setColumnHidden(2, not detailed) # Label
        self.table.setColumnHidden(5, not detailed) # Trace
        self.table.setColumnHidden(6, not detailed) # Type
        self.table.setColumnHidden(7, not detailed) # Ref
        self.table.setColumnHidden(8, not detailed) # Shape
        self.table.setColumnHidden(9, not detailed) # Color
        self.table.setColumnHidden(10, not detailed) # Delete
        
        QTimer.singleShot(50, self._adjust_window_width)

    def _adjust_window_width(self):
        # Calculate needed width exactly based on visible columns plus comfortable padding
        needed_width = self.table.verticalHeader().width() + self.table.horizontalHeader().length() + 75
        
        # Free the minimum width constraint so it can shrink
        self.setMinimumWidth(0)
        
        # Force the resize to perfectly wrap the contents
        self.resize(needed_width, self.height())

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

        stores = MarkerStore.all_stores()

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

        new_row_ids = [(id(store), m.id) for store, m, _ in all_rows]
        if new_row_ids == self._current_row_markers:
            self._update_existing_rows(all_rows)
            return

        self._populating = True
        self.table.setRowCount(0)
        self._current_row_markers = new_row_ids
        
        SHAPE_SYMBOLS = {
            MarkerShape.DIAMOND: "◆",
            MarkerShape.TRIANGLE_UP: "▲",
            MarkerShape.SQUARE: "■",
            MarkerShape.CROSS: "✖",
            MarkerShape.CIRCLE: "●",
            MarkerShape.STAR: "★"
        }

        for i, (store, m, graph_label) in enumerate(all_rows):
            self.table.insertRow(i)

            # Graph (read-only)
            graph_lbl = QLabel(f" {graph_label} ")
            graph_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(i, 0, graph_lbl)

            # ID (read-only)
            id_lbl = QLabel(f" {m.id} ")
            id_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(i, 1, id_lbl)

            # Label
            label_edit = QLineEdit(m.label)
            label_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label_edit.setMinimumWidth(30)
            label_edit.setMaximumWidth(80)
            label_edit.textChanged.connect(lambda text, s=store, mid=m.id: self._update_marker(s, mid, label=text))
            self.table.setCellWidget(i, 2, label_edit)

            # X
            x_spin = QDoubleSpinBox()
            x_spin.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            x_spin.setRange(-1e15, 1e15)
            x_spin.setDecimals(6)
            x_spin.setMinimumWidth(60)
            x_spin.setMaximumWidth(100)
            x_spin.setValue(m.x)
            x_spin.setKeyboardTracking(False)
            x_spin.valueChanged.connect(lambda val, s=store, mid=m.id: self._update_marker(s, mid, x=val))
            self.table.setCellWidget(i, 3, x_spin)

            # Y (read-only)
            import pyqtgraph as pg
            y_str = pg.siFormat(m.y, suffix='')
            y_lbl = QLabel(f" {y_str} ")
            y_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            y_lbl.setMinimumWidth(50)
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
            trace_box.setItemDelegate(self._combo_delegate)
            trace_box.setMaxVisibleItems(15)
            for k in keys:
                trace_box.addItem(str(k), k)
            idx = trace_box.findData(m.trace_key)
            if idx >= 0:
                trace_box.setCurrentIndex(idx)
            trace_box.currentIndexChanged.connect(lambda idx, s=store, mid=m.id, tb=trace_box: self._update_marker(s, mid, trace_key=tb.itemData(idx)))
            self.table.setCellWidget(i, 5, self._centered_widget(trace_box))

            # Type
            type_toggle = TypeToggleWidget(m.marker_type)
            type_toggle.typeChanged.connect(lambda t, s=store, mid=m.id: self._update_marker(s, mid, marker_type=t))
            self.table.setCellWidget(i, 6, self._centered_widget(type_toggle))

            # Ref — only show markers from the same store
            same_store_markers = [row for row in all_rows if row[0] is store]
            ref_box = QComboBox()
            ref_box.setItemDelegate(self._combo_delegate)
            ref_box.view().setMinimumWidth(80) # Ensure menu is wide enough
            ref_box.setMaxVisibleItems(15) # Show more items to avoid scrolling
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
            self.table.setCellWidget(i, 7, self._centered_widget(ref_box))

            # Shape
            shape_box = QComboBox()
            shape_box.setItemDelegate(self._combo_delegate)
            shape_box.view().setMinimumWidth(60)
            shape_box.setMaxVisibleItems(15)
            shape_box.setStyleSheet(f"font-size: 16px; color: {m.color};")
            for sh in MarkerShape:
                shape_box.addItem(SHAPE_SYMBOLS.get(sh, sh.name), sh)
            shape_box.setCurrentIndex(list(MarkerShape).index(m.shape))
            shape_box.currentIndexChanged.connect(lambda idx, s=store, mid=m.id, sb=shape_box: self._update_marker(s, mid, shape=sb.itemData(idx)))
            self.table.setCellWidget(i, 8, self._centered_widget(shape_box))

            # Color
            col_btn = QPushButton("")
            col_btn.setFixedSize(16, 16)
            col_btn.setStyleSheet(f"background-color: {m.color}; border-radius: 8px; margin: 4px;")
            col_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            col_btn.clicked.connect(lambda _, s=store, mid=m.id, c=m.color: self._pick_color(s, mid, c))
            self.table.setCellWidget(i, 9, self._centered_widget(col_btn))

            # Delete
            del_btn = QPushButton("\u2715")
            del_btn.setFixedSize(20, 20)
            del_btn.setStyleSheet("QPushButton { border: none; font-weight: bold; font-size: 14px; background: transparent; } QPushButton:hover { color: #ff5555; }")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda _, s=store, mid=m.id: s.remove_marker(mid))
            self.table.setCellWidget(i, 10, self._centered_widget(del_btn))

        self._populating = False

    def _update_existing_rows(self, all_rows):
        self._populating = True
        for i, (store, m, graph_label) in enumerate(all_rows):
            lbl = self.table.cellWidget(i, 0)
            if lbl: lbl.setText(f" {graph_label} ")

            edit = self.table.cellWidget(i, 2)
            if edit and edit.text() != m.label:
                edit.setText(m.label)
            
            x_spin = self.table.cellWidget(i, 3)
            if x_spin and x_spin.value() != m.x:
                x_spin.setValue(m.x)

            import pyqtgraph as pg
            y_str = pg.siFormat(m.y, suffix='')
            y_lbl = self.table.cellWidget(i, 4)
            if y_lbl and y_lbl.text() != f" {y_str} ":
                y_lbl.setText(f" {y_str} ")
                y_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            trace_box = self.table.cellWidget(i, 5)
            if trace_box and hasattr(trace_box, '_child_widget'):
                trace_box = trace_box._child_widget
                idx = trace_box.findData(m.trace_key)
                if idx >= 0 and trace_box.currentIndex() != idx:
                    trace_box.setCurrentIndex(idx)

            type_toggle = self.table.cellWidget(i, 6)
            if type_toggle and hasattr(type_toggle, '_child_widget'):
                type_toggle = type_toggle._child_widget
                if isinstance(type_toggle, TypeToggleWidget):
                    type_toggle.setType(m.marker_type)

            ref_box = self.table.cellWidget(i, 7)
            if ref_box and hasattr(ref_box, '_child_widget'):
                ref_box = ref_box._child_widget
                idx = ref_box.findData(m.ref_marker_id) if m.ref_marker_id else ref_box.findData(None)
                if idx >= 0 and ref_box.currentIndex() != idx:
                    ref_box.setCurrentIndex(idx)
                
                # Update enabled state
                is_rel = m.marker_type == MarkerType.RELATIVE
                if ref_box.isEnabled() != is_rel:
                    ref_box.setEnabled(is_rel)
                
            shape_box = self.table.cellWidget(i, 8)
            if shape_box and hasattr(shape_box, '_child_widget'):
                shape_box = shape_box._child_widget
                idx = list(MarkerShape).index(m.shape)
                if shape_box.currentIndex() != idx:
                    shape_box.setCurrentIndex(idx)
                style = f"font-size: 16px; color: {m.color};"
                if shape_box.styleSheet() != style:
                    shape_box.setStyleSheet(style)

            col_btn = self.table.cellWidget(i, 9)
            if col_btn and hasattr(col_btn, '_child_widget'):
                col_btn = col_btn._child_widget
                from PyQt6.QtGui import QColor
                style = f"background-color: {m.color}; border-radius: 8px; margin: 4px;"
                if col_btn.styleSheet() != style:
                    col_btn.setStyleSheet(style)
        self._populating = False

    def _update_marker(self, store, marker_id, **kwargs):
        if not self._populating:
            self._self_updating = True
            store.update_marker(marker_id, **kwargs)
            self._self_updating = False
            
            # Immediately synchronize UI for this specific update
            # We don't want a full rebuild (deferred), but we do want existing widgets to reflect the new state.
            stores = MarkerStore.all_stores()
            all_rows = []
            for s in stores:
                label = _store_label(s)
                for m in s.get_markers():
                    all_rows.append((s, m, label))
            
            # Sort as in _populate_table
            def safe_sort_key(row):
                try:
                    return int(row[1].id[1:])
                except ValueError:
                    return 999
            all_rows.sort(key=safe_sort_key)
            self._update_existing_rows(all_rows)

    def _centered_widget(self, widget, stretch=True):
        from PyQt6.QtWidgets import QWidget, QHBoxLayout
        from PyQt6.QtCore import Qt
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        if stretch:
            layout.addStretch()
        layout.addWidget(widget)
        if stretch:
            layout.addStretch()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container._child_widget = widget
        return container

    def _pick_color(self, store, marker_id, current_color):
        color = QColorDialog.getColor(QColor(current_color), self, "Pick Marker Color")
        if color.isValid():
            store.update_marker(marker_id, color=color.name())
