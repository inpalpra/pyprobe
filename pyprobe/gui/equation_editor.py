from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QPushButton, QLineEdit, QLabel, QHeaderView, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDrag
from PyQt6.QtCore import QMimeData

from pyprobe.core.equation_manager import EquationManager, Equation

class EquationEditorDialog(QDialog):
    """
    Dialog for managing mathematical equations.
    """
    _instance = None
    plot_requested = pyqtSignal(str)  # eq_id
    equation_added = pyqtSignal(str)  # eq_id
    equation_deleted = pyqtSignal(str)  # eq_id

    @classmethod
    def show_instance(cls, manager: EquationManager, parent=None):
        if cls._instance is not None:
            try:
                cls._instance.objectName()
                if cls._instance.isVisible():
                    cls._instance.raise_()
                    cls._instance.activateWindow()
                    return cls._instance
                cls._instance.deleteLater()
            except RuntimeError:
                pass
        cls._instance = cls(manager, parent)
        cls._instance.show()
        return cls._instance

    def __init__(self, manager: EquationManager, parent=None):
        super().__init__(parent)
        self._manager = manager
        
        self.setWindowTitle("Equation Editor")
        self.setMinimumSize(500, 300)
        self.setWindowFlag(Qt.WindowType.Tool)

        self._setup_ui()
        self._apply_theme()
        self._populate_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Equation", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.table)
        
        # Bottom buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("+ Add Equation")
        self.add_btn.clicked.connect(self._on_add_clicked)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _apply_theme(self):
        from .theme.theme_manager import ThemeManager
        c = ThemeManager.instance().current.colors
        self.setStyleSheet(f"""
            QDialog {{ background-color: {c['bg_dark']}; color: {c['text_primary']}; }}
            QTableWidget {{ background-color: {c['bg_dark']}; gridline-color: {c['border_default']}; border: none; }}
            QHeaderView::section {{ background-color: {c['bg_dark']}; color: {c['text_secondary']}; border: none; border-bottom: 1px solid {c['border_default']}; padding: 4px; }}
            QLineEdit {{ background-color: {c['bg_medium']}; color: {c['text_primary']}; border: 1px solid {c['border_default']}; border-radius: 2px; padding: 2px; }}
            QPushButton {{ background-color: {c['bg_medium']}; color: {c['text_primary']}; border-radius: 2px; padding: 4px 8px; }}
            QPushButton:hover {{ background-color: {c['border_default']}; }}
        """)

    def _populate_table(self):
        self.table.setRowCount(0)
        for eq in self._manager.equations.values():
            self._add_row(eq)

    def _add_row(self, eq: Equation):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # ID label (Draggable)
        id_label = DraggableLabel(eq.id)
        id_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        id_label.setStyleSheet("color: #00ffff; font-weight: bold; font-family: monospace;")
        self.table.setCellWidget(row, 0, id_label)
        
        # Equation input
        edit = QLineEdit(eq.expression)
        edit.textChanged.connect(lambda text, eid=eq.id: self._on_expression_changed(eid, text))
        self.table.setCellWidget(row, 1, edit)
        
        # Status icon / Delete button
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(4, 0, 4, 0)
        
        plot_btn = QPushButton("Plot")
        plot_btn.setFixedSize(40, 20)
        plot_btn.setStyleSheet("font-size: 10px; padding: 0px;")
        plot_btn.clicked.connect(lambda _, eid=eq.id: self.plot_requested.emit(eid))
        status_layout.addWidget(plot_btn)

        status_lbl = QLabel("?")
        status_layout.addWidget(status_lbl)
        
        del_btn = QPushButton("×")
        del_btn.setFixedSize(20, 20)
        del_btn.setStyleSheet("QPushButton { background: transparent; color: #555555; } QPushButton:hover { color: #ff5555; }")
        del_btn.clicked.connect(lambda _, eid=eq.id: self._on_delete_clicked(eid))
        status_layout.addWidget(del_btn)
        
        container = QWidget()
        container.setLayout(status_layout)
        self.table.setCellWidget(row, 2, container)

    def _on_add_clicked(self):
        eq = self._manager.add_equation()
        self._add_row(eq)
        self.equation_added.emit(eq.id)

    def _on_delete_clicked(self, eq_id: str):
        self._manager.remove_equation(eq_id)
        self._populate_table()
        self.equation_deleted.emit(eq_id)

    def _on_expression_changed(self, eq_id: str, text: str):
        self._manager.update_expression(eq_id, text)

class DraggableLabel(QLabel):
    """
    A label that can be dragged to plots.
    """
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < 5:
            return

        drag = QDrag(self)
        mime = QMimeData()
        # Custom mime type for equation traces
        mime.setData("application/x-pyprobe-equation", self.text().encode())
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)
