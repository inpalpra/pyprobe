"""
File tree panel for folder browsing.
Shows .py files in a directory tree. Single click selects a file.
"""

import os
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QLabel, QHeaderView,
    QToolButton,
)
from PyQt6.QtCore import (
    pyqtSignal, Qt, QDir, QModelIndex, QSortFilterProxyModel
)
from PyQt6.QtGui import QFileSystemModel, QFont


class PyFileFilterProxy(QSortFilterProxyModel):
    """Filter to show only .py files and directories containing them."""

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        if not index.isValid():
            return False

        file_info = model.fileInfo(index)
        if file_info.isDir():
            # Show directories (Qt will hide empty ones naturally since
            # their children won't pass the filter)
            return True
        # Show only .py files
        return file_info.suffix() == "py"


class FileTreePanel(QWidget):
    """
    File tree panel showing .py files in a folder.

    Signals:
        file_selected(str): Emitted when a .py file is clicked.
    """

    file_selected = pyqtSignal(str)
    collapse_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumWidth(150)
        self._current_file: Optional[str] = None
        self._root_path: Optional[str] = None
        self._setup_ui()

        from .theme.theme_manager import ThemeManager
        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.current)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header row: label + collapse button
        header_row = QWidget()
        header_row.setObjectName("fileTreeHeader")
        h_layout = QHBoxLayout(header_row)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        self._header = QLabel("FILES")
        h_layout.addWidget(self._header)
        h_layout.addStretch()

        self._collapse_btn = QToolButton()
        self._collapse_btn.setText("\u25c2")  # ◂
        self._collapse_btn.setToolTip("Hide file explorer")
        self._collapse_btn.setFixedSize(22, 22)
        self._collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._collapse_btn.clicked.connect(self.collapse_requested.emit)
        h_layout.addWidget(self._collapse_btn)

        layout.addWidget(header_row)

        # File system model
        self._fs_model = QFileSystemModel()
        self._fs_model.setReadOnly(True)

        # Proxy filter for .py only
        self._proxy = PyFileFilterProxy()
        self._proxy.setSourceModel(self._fs_model)
        self._proxy.setRecursiveFilteringEnabled(True)

        # Tree view
        self._tree = QTreeView()
        self._tree.setModel(self._proxy)
        self._tree.setHeaderHidden(True)
        self._tree.setAnimated(True)
        self._tree.setIndentation(16)
        self._tree.setRootIsDecorated(True)

        # Hide size, type, date columns — show only name
        for col in (1, 2, 3):
            self._tree.setColumnHidden(col, True)

        self._tree.clicked.connect(self._on_clicked)
        layout.addWidget(self._tree)

    def _apply_theme(self, theme):
        c = theme.colors
        self._header.setStyleSheet(
            f"color: {c['accent_primary']}; background-color: {c['bg_darkest']}; "
            f"padding: 6px 8px; font-weight: bold; font-size: 10px;"
        )
        self._header.parentWidget().setStyleSheet(
            f"background-color: {c['bg_darkest']}; "
            f"border-bottom: 1px solid {c['border_default']};"
        )
        self._collapse_btn.setStyleSheet(
            f"QToolButton {{ color: {c['text_muted']}; background: transparent; "
            f"border: none; font-size: 11px; }}"
            f"QToolButton:hover {{ color: {c['accent_primary']}; }}"
        )
        self._tree.setStyleSheet(f"""
            QTreeView {{
                background-color: {c['bg_darkest']};
                border: none;
                color: {c['text_secondary']};
                font-size: 11px;
            }}
            QTreeView::item {{
                padding: 3px 4px;
                border: none;
            }}
            QTreeView::item:hover {{
                background-color: {c['bg_medium']};
                color: {c['text_primary']};
            }}
            QTreeView::item:selected {{
                background-color: {c['bg_medium']};
                color: {c['accent_primary']};
                border-left: 2px solid {c['accent_primary']};
            }}
            QTreeView::branch {{
                background-color: {c['bg_darkest']};
            }}
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {{
                image: none;
                border-image: none;
            }}
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {{
                image: none;
                border-image: none;
            }}
        """)

    def set_root(self, folder_path: str):
        """Set the root directory for the file tree."""
        folder_path = os.path.abspath(folder_path)
        self._root_path = folder_path

        # Set root on the source model
        source_root = self._fs_model.setRootPath(folder_path)
        # Map to proxy index
        proxy_root = self._proxy.mapFromSource(source_root)
        self._tree.setRootIndex(proxy_root)

        # Update header
        folder_name = os.path.basename(folder_path)
        self._header.setText(folder_name.upper())
        self._header.setToolTip(folder_path)

    def highlight_file(self, file_path: str):
        """Highlight the currently-loaded file in the tree."""
        self._current_file = os.path.abspath(file_path)
        source_index = self._fs_model.index(self._current_file)
        if source_index.isValid():
            proxy_index = self._proxy.mapFromSource(source_index)
            self._tree.setCurrentIndex(proxy_index)
            self._tree.scrollTo(proxy_index)

    def clear(self):
        """Reset to no-folder state."""
        self._root_path = None
        self._current_file = None
        self._header.setText("FILES")

    def _on_clicked(self, proxy_index: QModelIndex):
        """Handle click on a tree item."""
        source_index = self._proxy.mapToSource(proxy_index)
        if not source_index.isValid():
            return

        file_info = self._fs_model.fileInfo(source_index)
        if file_info.isFile() and file_info.suffix() == "py":
            file_path = file_info.absoluteFilePath()
            self.file_selected.emit(file_path)
