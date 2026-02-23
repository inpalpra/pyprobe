"""Simple scalar display plugin - shows current value only."""
from typing import Any, Optional, Tuple
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt

from ..base import ProbePlugin
from ...core.data_classifier import DTYPE_SCALAR


class ScalarDisplayWidget(QWidget):
    """Simple numeric display for scalar values."""
    
    def __init__(self, var_name: str, color: QColor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._var_name = var_name
        self._color = color
        self._has_data = False
        self._theme_colors: dict = {}
        self._setup_ui()

        from ...gui.theme.theme_manager import ThemeManager
        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.current)

    def _setup_ui(self):
        """Create the scalar display widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Header
        self._name_label = QLabel(self._var_name)
        self._name_label.setFont(QFont("JetBrains Mono", 11, QFont.Weight.Bold))
        self._name_label.setStyleSheet(f"color: {self._color.name()};")
        layout.addWidget(self._name_label)

        # Value
        self._value_label = QLabel("Nothing to show")
        self._value_label.setFont(QFont("JetBrains Mono", 14))
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._value_label)

        # Info
        self._info_label = QLabel("")
        self._info_label.setFont(QFont("JetBrains Mono", 9))
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._info_label)

        layout.addStretch()
        self.setMinimumSize(150, 100)

    def _apply_theme(self, theme) -> None:
        c = theme.colors
        self._theme_colors = c
        self._info_label.setStyleSheet(f"color: {c['text_secondary']};")
        if self._has_data:
            self._value_label.setStyleSheet(f"color: {c['text_primary']};")
        else:
            self._value_label.setStyleSheet(f"color: {c['text_muted']};")

    def set_color(self, color: QColor) -> None:
        """Update the probe color (name label)."""
        self._color = color
        self._name_label.setStyleSheet(f"color: {color.name()};")

    def update_data(self, value: Any, dtype: str, shape: Optional[tuple] = None, source_info: str = "") -> None:
        """Update the display with new scalar value."""
        if not self._has_data:
            self._has_data = True
            self._value_label.setFont(QFont("JetBrains Mono", 24, QFont.Weight.Bold))
            c = self._theme_colors
            self._value_label.setStyleSheet(f"color: {c.get('text_primary', '#ffffff')};")

        
        if value is None:
            display_text = "--"
            type_text = "None"
        elif isinstance(value, complex):
            # Format complex
            sign = "+" if value.imag >= 0 else "-"
            display_text = f"{value.real:.4g} {sign} {abs(value.imag):.4g}j"
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


class ScalarDisplayPlugin(ProbePlugin):
    """Plugin for displaying scalar values as simple text."""
    
    name = "Value"
    icon = "number"
    priority = 50  # Lower priority than History for scalars
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype == DTYPE_SCALAR
    
    def create_widget(self, var_name: str, color: QColor, parent: Optional[QWidget] = None) -> QWidget:
        return ScalarDisplayWidget(var_name, color, parent)
    
    def update(self, widget: QWidget, value: Any, dtype: str,
               shape: Optional[Tuple[int, ...]] = None,
               source_info: str = "") -> None:
        if isinstance(widget, ScalarDisplayWidget):
            widget.update_data(value, dtype, shape, source_info)
