"""
Variable watch list widget.
"""

from typing import Optional, Set
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt


class WatchListWidget(QWidget):
    """
    Widget for managing the list of watched variables.

    Users can add variable names to watch, and they'll be
    intercepted when the script runs.
    """

    # Signals
    variable_added = pyqtSignal(str)      # var_name
    variable_removed = pyqtSignal(str)    # var_name
    throttle_changed = pyqtSignal(str, str, float)  # var_name, strategy, param

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._watched: Set[str] = set()
        self._setup_ui()

    def _setup_ui(self):
        """Create the watch list UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Title
        title = QLabel("Watch Variables")
        title.setStyleSheet("color: #00ffff; font-weight: bold; font-size: 12px;")
        layout.addWidget(title)

        # Input row
        input_row = QHBoxLayout()

        self._input = QLineEdit()
        self._input.setPlaceholderText("Variable name...")
        self._input.returnPressed.connect(self._add_variable)
        input_row.addWidget(self._input)

        self._add_btn = QPushButton("+")
        self._add_btn.setFixedWidth(30)
        self._add_btn.clicked.connect(self._add_variable)
        input_row.addWidget(self._add_btn)

        layout.addLayout(input_row)

        # List of watched variables
        self._list = QListWidget()
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._list)

        # Help text
        help_label = QLabel("Double-click to remove")
        help_label.setStyleSheet("color: #666666; font-size: 9px;")
        layout.addWidget(help_label)

    def _add_variable(self):
        """Add a variable to the watch list."""
        var_name = self._input.text().strip()
        if not var_name:
            return

        if var_name in self._watched:
            return

        self._watched.add(var_name)

        # Add to list widget
        item = QListWidgetItem(var_name)
        item.setData(Qt.ItemDataRole.UserRole, var_name)
        self._list.addItem(item)

        # Clear input
        self._input.clear()

        # Emit signal
        self.variable_added.emit(var_name)

    def _remove_variable(self, var_name: str):
        """Remove a variable from the watch list."""
        if var_name not in self._watched:
            return

        self._watched.discard(var_name)

        # Remove from list widget
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == var_name:
                self._list.takeItem(i)
                break

        # Emit signal
        self.variable_removed.emit(var_name)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on list item (remove)."""
        var_name = item.data(Qt.ItemDataRole.UserRole)
        self._remove_variable(var_name)

    def _show_context_menu(self, pos):
        """Show context menu for list items."""
        item = self._list.itemAt(pos)
        if item is None:
            return

        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)

        var_name = item.data(Qt.ItemDataRole.UserRole)

        remove_action = menu.addAction("Remove")
        remove_action.triggered.connect(lambda: self._remove_variable(var_name))

        menu.exec(self._list.mapToGlobal(pos))

    def get_watched_variables(self) -> Set[str]:
        """Get the set of currently watched variable names."""
        return self._watched.copy()

    def add_variable_programmatically(self, var_name: str):
        """Add a variable without user input (e.g., from command line)."""
        if var_name in self._watched:
            return

        self._watched.add(var_name)

        item = QListWidgetItem(var_name)
        item.setData(Qt.ItemDataRole.UserRole, var_name)
        self._list.addItem(item)

        self.variable_added.emit(var_name)
