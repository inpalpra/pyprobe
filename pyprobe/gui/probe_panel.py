"""
Container widget for probe panels with flow layout.
"""

from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QGridLayout, QFrame, QLabel
)
from PyQt6.QtCore import Qt

from ..plots.base_plot import BasePlot
from ..plots.plot_factory import create_plot


class ProbePanel(QFrame):
    """
    Container for a single probe (plot widget).

    Provides a bordered frame around the plot with consistent sizing.
    """

    def __init__(
        self,
        var_name: str,
        dtype: str,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._var_name = var_name
        self._dtype = dtype
        self._plot: Optional[BasePlot] = None

        self._setup_ui()

    def _setup_ui(self):
        """Create the panel UI."""
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setStyleSheet("""
            ProbePanel {
                border: 1px solid #333333;
                border-radius: 6px;
                background-color: #0d0d0d;
            }
            ProbePanel:hover {
                border-color: #00ffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Create the appropriate plot widget
        self._plot = create_plot(self._var_name, self._dtype, self)
        layout.addWidget(self._plot)

        # Set minimum size
        self.setMinimumSize(300, 250)

    def update_data(self, value, dtype: str, shape=None, source_info: str = ""):
        """Update the plot with new data."""
        if self._plot:
            self._plot.update_data(value, dtype, shape, source_info)

    @property
    def var_name(self) -> str:
        return self._var_name


class ProbePanelContainer(QScrollArea):
    """
    Scrollable container for multiple probe panels.

    Uses a grid layout to arrange panels.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._panels: Dict[str, ProbePanel] = {}
        self._setup_ui()

    def _setup_ui(self):
        """Create the container UI."""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Content widget
        self._content = QWidget()
        self.setWidget(self._content)

        # Grid layout for panels
        self._layout = QGridLayout(self._content)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)

        # Placeholder label
        self._placeholder = QLabel("Add variables to the watch list to probe them")
        self._placeholder.setStyleSheet("color: #666666; font-size: 14px;")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._placeholder, 0, 0)

        # Track grid position
        self._next_row = 0
        self._next_col = 0
        self._cols = 2  # 2 columns by default

    def create_panel(self, var_name: str, dtype: str) -> ProbePanel:
        """Create a new probe panel for a variable."""
        if var_name in self._panels:
            return self._panels[var_name]

        # Hide placeholder
        self._placeholder.hide()

        # Create panel
        panel = ProbePanel(var_name, dtype, self._content)
        self._panels[var_name] = panel

        # Add to grid
        self._layout.addWidget(panel, self._next_row, self._next_col)

        # Advance position
        self._next_col += 1
        if self._next_col >= self._cols:
            self._next_col = 0
            self._next_row += 1

        return panel

    def remove_panel(self, var_name: str):
        """Remove a probe panel."""
        if var_name not in self._panels:
            return

        panel = self._panels.pop(var_name)
        self._layout.removeWidget(panel)
        panel.deleteLater()

        # Re-layout remaining panels
        self._relayout_panels()

        # Show placeholder if empty
        if not self._panels:
            self._placeholder.show()

    def _relayout_panels(self):
        """Re-layout panels after removal."""
        # Remove all panels from layout
        for panel in self._panels.values():
            self._layout.removeWidget(panel)

        # Re-add in order
        self._next_row = 0
        self._next_col = 0

        for panel in self._panels.values():
            self._layout.addWidget(panel, self._next_row, self._next_col)
            self._next_col += 1
            if self._next_col >= self._cols:
                self._next_col = 0
                self._next_row += 1

    def get_panel(self, var_name: str) -> Optional[ProbePanel]:
        """Get a panel by variable name."""
        return self._panels.get(var_name)
