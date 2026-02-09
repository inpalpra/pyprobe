"""
Floating scalar watch window - displays all Alt+clicked scalars in one place.
"""
from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from pyprobe.core.anchor import ProbeAnchor


class ScalarWatchWindow(QWidget):
    """
    Floating, always-on-top window for displaying scalars probed with Alt+click.
    
    Shows each scalar as a row with symbol name and current value.
    """
    
    # Signal when a scalar is removed from watch
    scalar_removed = pyqtSignal(object)  # ProbeAnchor
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        
        self.setWindowTitle("Scalar Watch")
        self.setMinimumSize(250, 150)
        self.resize(300, 200)
        
        # Track scalars: anchor -> (label_widget, value_widget, color)
        self._scalars: Dict[ProbeAnchor, tuple] = {}
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """Build the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Header
        header = QLabel("Scalar Watch (Alt+Click)")
        header.setStyleSheet("color: #00ffff; font-weight: bold; font-size: 12px;")
        layout.addWidget(header)
        
        # Scroll area for scalars
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(2)
        self._content_layout.addStretch()  # Push items to top
        
        scroll.setWidget(self._content)
        layout.addWidget(scroll)
        
        # Placeholder when empty
        self._placeholder = QLabel("Alt+click scalars in code to watch them here")
        self._placeholder.setStyleSheet("color: #666666; font-style: italic;")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content_layout.insertWidget(0, self._placeholder)
    
    def _apply_styles(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a2e;
                color: #e0e0e0;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
            }
            QScrollArea {
                background-color: transparent;
            }
        """)
    
    def add_scalar(self, anchor: ProbeAnchor, color: QColor) -> None:
        """Add a scalar to the watch window."""
        if anchor in self._scalars:
            return  # Already watching
        
        # Hide placeholder
        self._placeholder.hide()
        
        # Create row widget
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(4, 2, 4, 2)
        row_layout.setSpacing(8)
        
        # Symbol name
        name_label = QLabel(anchor.symbol)
        name_label.setStyleSheet(f"color: {color.name()}; font-weight: bold;")
        name_label.setMinimumWidth(100)
        row_layout.addWidget(name_label)
        
        # Value display
        value_label = QLabel("--")
        value_label.setStyleSheet("color: #e0e0e0; font-family: monospace;")
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        row_layout.addWidget(value_label, 1)
        
        # Remove button
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ff6666;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #333;
            }
        """)
        remove_btn.clicked.connect(lambda: self._remove_scalar(anchor))
        row_layout.addWidget(remove_btn)
        
        # Add to layout (before the stretch)
        self._content_layout.insertWidget(self._content_layout.count() - 1, row)
        
        # Track
        self._scalars[anchor] = (row, name_label, value_label, color)
        
        # Show window if hidden
        if not self.isVisible():
            self.show()
    
    def update_scalar(self, anchor: ProbeAnchor, value) -> None:
        """Update the displayed value for a scalar."""
        if anchor not in self._scalars:
            return
        
        _, _, value_label, _ = self._scalars[anchor]
        
        # Format value
        if isinstance(value, float):
            if abs(value) < 0.01 or abs(value) > 1000:
                text = f"{value:.4e}"
            else:
                text = f"{value:.4f}"
        elif isinstance(value, complex):
            text = f"{value.real:.2f} + {value.imag:.2f}j"
        else:
            text = str(value)
        
        value_label.setText(text)
    
    def _remove_scalar(self, anchor: ProbeAnchor) -> None:
        """Remove a scalar from the watch window."""
        if anchor not in self._scalars:
            return
        
        row, _, _, _ = self._scalars.pop(anchor)
        row.deleteLater()
        
        # Show placeholder if empty
        if not self._scalars:
            self._placeholder.show()
        
        # Emit signal
        self.scalar_removed.emit(anchor)
    
    def remove_scalar(self, anchor: ProbeAnchor) -> None:
        """Public method to remove a scalar (e.g., when probe is removed)."""
        self._remove_scalar(anchor)
    
    def has_scalar(self, anchor: ProbeAnchor) -> bool:
        """Check if a scalar is being watched."""
        return anchor in self._scalars
    
    def get_watched_anchors(self) -> list:
        """Get all watched anchors."""
        return list(self._scalars.keys())
