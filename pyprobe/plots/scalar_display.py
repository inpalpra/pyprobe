"""
Scalar display widget for single numeric values.
"""

from typing import Optional, Any
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from .base_plot import BasePlot


class ScalarDisplay(BasePlot):
    """
    Display widget for scalar values (int, float, complex).

    Shows the value in a large, easy-to-read format.
    """

    def __init__(self, var_name: str, parent: Optional[QWidget] = None):
        super().__init__(var_name, parent)

        self._value: Any = None
        self._setup_ui()

    def _setup_ui(self):
        """Create the scalar display widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Header with variable name
        self._name_label = QLabel(self._var_name)
        self._name_label.setFont(QFont("JetBrains Mono", 11, QFont.Weight.Bold))
        self._name_label.setStyleSheet("color: #ffff00;")  # Yellow
        layout.addWidget(self._name_label)

        # Large value display
        self._value_label = QLabel("Nothing to show")
        self._value_label.setFont(QFont("JetBrains Mono", 14))
        self._value_label.setStyleSheet("color: #666666;")  # Gray for placeholder
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._has_data = False  # Track if we've received data
        layout.addWidget(self._value_label)

        # Type/info label
        self._info_label = QLabel("")
        self._info_label.setFont(QFont("JetBrains Mono", 9))
        self._info_label.setStyleSheet("color: #888888;")
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._info_label)

        layout.addStretch()

        # Set minimum size
        self.setMinimumSize(150, 100)

    def update_data(
        self,
        value: Any,
        dtype: str,
        shape: Optional[tuple] = None,
        source_info: str = ""
    ):
        """Update the display with new scalar value."""
        self._value = value

        # Switch from placeholder to active styling on first data
        if not self._has_data:
            self._has_data = True
            self._value_label.setFont(QFont("JetBrains Mono", 24, QFont.Weight.Bold))
            self._value_label.setStyleSheet("color: #00ff00;")  # Green

        # Format the value
        if value is None:
            display_text = "--"
            type_text = "None"
        elif isinstance(value, complex):
            # Format complex number
            if value.imag >= 0:
                display_text = f"{value.real:.4g} + {value.imag:.4g}j"
            else:
                display_text = f"{value.real:.4g} - {abs(value.imag):.4g}j"
            type_text = f"complex | {source_info}"
        elif isinstance(value, float):
            display_text = f"{value:.6g}"
            type_text = f"float | {source_info}"
        elif isinstance(value, int):
            display_text = str(value)
            type_text = f"int | {source_info}"
        else:
            display_text = str(value)[:20]
            type_text = f"{type(value).__name__} | {source_info}"

        self._value_label.setText(display_text)
        self._info_label.setText(type_text)
