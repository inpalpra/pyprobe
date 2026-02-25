"""Scalar watch sidebar - displays all Alt+clicked scalars in one place.
"""
from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QToolButton, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from pyprobe.core.anchor import ProbeAnchor


class ScalarWatchSidebar(QWidget):
    """
    Sidebar widget for displaying scalars probed with Alt+click.
    
    Shows each scalar vertically stacked: label above value.
    """
    
    # Signal when a scalar is removed from watch
    scalar_removed = pyqtSignal(object)  # ProbeAnchor
    collapse_requested = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.setMinimumWidth(150)
        
        # Track scalars: anchor -> (card_widget, value_widget)
        self._scalars: Dict[ProbeAnchor, tuple] = {}
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """Build the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header row: collapse button + label
        header_row = QWidget()
        header_row.setObjectName("watchHeader")
        h_layout = QHBoxLayout(header_row)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        header = QLabel("Watch")
        header.setObjectName("sidebarHeader")
        h_layout.addWidget(header)
        h_layout.addStretch()

        self._collapse_btn = QToolButton()
        self._collapse_btn.setText("\u25b8")  # ▸
        self._collapse_btn.setToolTip("Hide watch panel")
        self._collapse_btn.setFixedSize(22, 22)
        self._collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._collapse_btn.clicked.connect(self.collapse_requested.emit)
        h_layout.addWidget(self._collapse_btn)

        layout.addWidget(header_row)
        
        # Scroll area for scalars
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(12)
        self._content_layout.addStretch()  # Push items to top
        
        scroll.setWidget(self._content)
        layout.addWidget(scroll)
        
        self._scroll = scroll
        
        # Placeholder when empty
        self._placeholder = QLabel("Alt+click scalars\nto watch")
        self._placeholder.setObjectName("placeholder")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setWordWrap(True)
        self._content_layout.insertWidget(0, self._placeholder)
    
    def _apply_styles(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QWidget {
                background-color: #000000;
                color: #e0e0e0;
            }
            QScrollArea {
                background-color: transparent;
            }
            QLabel#sidebarHeader {
                color: #888888;
                font-size: 12px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 1px;
                padding-bottom: 4px;
            }
            QWidget#watchHeader {
                border-bottom: 1px solid #2a2a4a;
            }
            QToolButton {
                color: #555555;
                background: transparent;
                border: none;
                font-size: 11px;
            }
            QToolButton:hover {
                color: #00ccff;
            }
            QLabel#placeholder {
                color: #555555;
                font-style: italic;
                font-size: 11px;
            }
            QLabel#scalarLabel {
                color: #888888;
                font-size: 11px;
                font-family: 'SF Pro Text', 'Segoe UI', sans-serif;
            }
            QLabel#scalarValue {
                color: #ffffff;
                font-size: 20px;
                font-family: 'JetBrains Mono', 'SF Mono', 'Consolas', monospace;
                font-weight: 500;
            }
            QWidget#scalarCard {
                background-color: #1e1e32;
                border-radius: 4px;
            }
            QPushButton#removeBtn {
                background-color: transparent;
                color: #555555;
                border: none;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#removeBtn:hover {
                color: #ff6666;
            }
        """)
    

    
    def add_scalar(self, anchor: ProbeAnchor, color: QColor, trace_id: str) -> None:
        """Add a scalar to the watch window."""
        if anchor in self._scalars:
            return  # Already watching
        
        # Hide placeholder
        self._placeholder.hide()
        
        # Create card widget with vertical layout
        card = QWidget()
        card.setObjectName("scalarCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 10)
        card_layout.setSpacing(2)
        
        # Top row: label + remove button
        top_row = QWidget()
        top_layout = QHBoxLayout(top_row) # Change to horizontal for trace_id + symbol
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)
        
        # Trace ID label (e.g., tr0)
        id_label = QLabel(trace_id)
        id_label.setStyleSheet("color: #00ffff; font-weight: bold; font-family: monospace; font-size: 10px;")
        top_layout.addWidget(id_label)

        # Label with highlight background (like code viewer probes)
        # Use semi-transparent fill with solid border
        name_label = QLabel(anchor.symbol)
        name_label.setObjectName("scalarLabel")
        name_label.setStyleSheet(f"""
            color: #ffffff;
            background-color: rgba({color.red()}, {color.green()}, {color.blue()}, 60);
            border: 1px solid {color.name()};
            border-radius: 2px;
            padding: 1px 4px;
        """)
        top_layout.addWidget(name_label)
        top_layout.addStretch()
        
        card_layout.addWidget(top_row)
        
        # Value (large, bright)
        value_label = QLabel("--")
        value_label.setObjectName("scalarValue")
        card_layout.addWidget(value_label)
        
        # Remove button (positioned at top-right corner)
        remove_btn = QPushButton("×")
        remove_btn.setObjectName("removeBtn")
        remove_btn.setFixedSize(20, 20)
        remove_btn.clicked.connect(lambda: self._remove_scalar(anchor))
        remove_btn.setParent(card)
        remove_btn.move(card.width() - 24, 4)
        
        # Re-position button on resize
        def reposition_btn():
            remove_btn.move(card.width() - 24, 4)
        card.resizeEvent = lambda e: reposition_btn()
        
        # Add to layout (before the stretch)
        self._content_layout.insertWidget(self._content_layout.count() - 1, card)
        
        # Track
        self._scalars[anchor] = (card, value_label)
    
    def update_scalar(self, anchor: ProbeAnchor, value) -> None:
        """Update the displayed value for a scalar."""
        if anchor not in self._scalars:
            return
        
        _, value_label = self._scalars[anchor]
        
        # Format value
        if isinstance(value, float):
            if abs(value) < 0.01 or abs(value) > 1000:
                text = f"{value:.4e}"
            else:
                text = f"{value:.4f}"
        elif isinstance(value, complex):
            text = f"{value.real:.2f}+{value.imag:.2f}j"
        else:
            text = str(value)
        
        value_label.setText(text)
    
    def _remove_scalar(self, anchor: ProbeAnchor) -> None:
        """Remove a scalar from the watch window."""
        if anchor not in self._scalars:
            return
        
        card, _ = self._scalars.pop(anchor)
        card.deleteLater()
        
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

    def clear(self) -> None:
        """Remove all watched scalars."""
        for anchor in list(self._scalars.keys()):
            self._remove_scalar(anchor)
