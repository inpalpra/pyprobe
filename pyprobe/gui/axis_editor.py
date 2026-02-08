"""
Inline editor for axis min/max values.
Appears over the tick label when user double-clicks.
Commits on Enter, cancels on Escape.
"""

from PyQt6.QtWidgets import QLineEdit, QWidget
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QDoubleValidator

from pyprobe.logging import get_logger
logger = get_logger(__name__)


class AxisEditor(QLineEdit):
    """Inline editor for axis min/max values.
    
    Signals:
        value_committed(float): New value accepted
        editing_cancelled(): Escape pressed or focus lost
    """
    
    value_committed = pyqtSignal(float)
    editing_cancelled = pyqtSignal()
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._original_value: float = 0.0
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configure the editor appearance."""
        self.setFont(QFont("JetBrains Mono", 10))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedWidth(80)
        self.setFixedHeight(22)
        
        # Validator for numeric input
        validator = QDoubleValidator()
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.setValidator(validator)
        
        # Dark theme styling
        self.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a2e;
                color: #00ffff;
                border: 1px solid #00ffff;
                border-radius: 3px;
                padding: 2px 4px;
                selection-background-color: #00ffff;
                selection-color: #1a1a2e;
            }
        """)
        
        self.hide()
    
    def show_at(self, x: int, y: int, initial_value: float) -> None:
        """Show editor at position with initial value."""
        self._original_value = initial_value
        
        # Format value intelligently
        if abs(initial_value) < 0.01 or abs(initial_value) >= 10000:
            text = f"{initial_value:.4e}"
        else:
            text = f"{initial_value:.4g}"
        
        self.setText(text)
        self.move(x - self.width() // 2, y - self.height() // 2)
        self.show()
        self.setFocus()
        self.selectAll()
        logger.debug(f"AxisEditor shown at ({x}, {y}) with value {initial_value}")
    
    def keyPressEvent(self, event) -> None:
        """Handle Enter and Escape keys."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._commit()
        elif event.key() == Qt.Key.Key_Escape:
            self._cancel()
        else:
            super().keyPressEvent(event)
    
    def focusOutEvent(self, event) -> None:
        """Cancel on focus loss."""
        super().focusOutEvent(event)
        if self.isVisible():
            self._cancel()
    
    def _commit(self) -> None:
        """Commit the current value."""
        text = self.text().strip()
        try:
            value = float(text)
            logger.debug(f"AxisEditor committed value: {value}")
            self.hide()
            self.value_committed.emit(value)
        except ValueError:
            logger.debug(f"AxisEditor invalid input: {text}")
            # Flash red border briefly
            self.setStyleSheet(self.styleSheet().replace("#00ffff", "#ff4444"))
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(300, lambda: self.setStyleSheet(
                self.styleSheet().replace("#ff4444", "#00ffff")))
    
    def _cancel(self) -> None:
        """Cancel editing and hide."""
        self.hide()
        logger.debug("AxisEditor cancelled")
        self.editing_cancelled.emit()
