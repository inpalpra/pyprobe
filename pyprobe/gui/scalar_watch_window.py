"""
Floating scalar watch window - displays all Alt+clicked scalars in one place.
"""
from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, 
    QPushButton, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtGui import QColor

from pyprobe.core.anchor import ProbeAnchor


class ScalarWatchWindow(QWidget):
    """
    Floating, always-on-top window for displaying scalars probed with Alt+click.
    
    Shows each scalar vertically stacked: label above value.
    """
    
    # Signal when a scalar is removed from watch
    scalar_removed = pyqtSignal(object)  # ProbeAnchor
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        
        self.setWindowTitle("Scalar Watch")
        self.setMinimumSize(200, 120)
        self.resize(220, 200)
        
        # Track scalars: anchor -> (card_widget, value_widget)
        self._scalars: Dict[ProbeAnchor, tuple] = {}
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """Build the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
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
        
        # Install event filter on viewport to allow dragging from inside scroll area
        scroll.viewport().installEventFilter(self)
        self._scroll = scroll
        
        # Placeholder when empty
        self._placeholder = QLabel("Alt+click scalars to watch")
        self._placeholder.setObjectName("placeholder")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content_layout.insertWidget(0, self._placeholder)
    
    def _apply_styles(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QWidget {
                background-color: #16162a;
                color: #e0e0e0;
            }
            QScrollArea {
                background-color: transparent;
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
    

    
    def eventFilter(self, obj, event):
        """Handle mouse events from scroll area viewport manually."""
        if hasattr(self, '_scroll') and obj == self._scroll.viewport():
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    # We don't accept/return True so scroll area still gets it (e.g. for focus)
            elif event.type() == QEvent.Type.MouseMove:
                if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, '_drag_offset'):
                    self.move(event.globalPosition().toPoint() - self._drag_offset)
                    # Don't consume so we don't block other behaviors?
                    # But if we move, maybe we *shouldn't* scroll. 
                    # If we return True, we block it.
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        """Handle mouse press to start dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.pos()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move to drag window."""
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, '_drag_offset'):
            self.move(self.mapToGlobal(event.pos()) - self._drag_offset)
            event.accept()
        super().mouseMoveEvent(event)
    
    def add_scalar(self, anchor: ProbeAnchor, color: QColor) -> None:
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
        top_layout = QVBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)
        
        # Label (small, muted)
        name_label = QLabel(anchor.symbol)
        name_label.setObjectName("scalarLabel")
        card_layout.addWidget(name_label)
        
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
        
        # Show window if hidden
        if not self.isVisible():
            self.show()
    
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
