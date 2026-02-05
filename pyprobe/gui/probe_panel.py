"""
Container widget for probe panels with flow layout.
"""

from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ..core.anchor import ProbeAnchor
from ..plots.base_plot import BasePlot
from ..plots.plot_factory import create_plot
from .probe_state import ProbeState
from .probe_state_indicator import ProbeStateIndicator
from .animations import ProbeAnimations


class ProbePanel(QFrame):
    """
    Container for a single probe (plot widget).

    Provides a bordered frame around the plot with consistent sizing,
    state indicator, identity label, and animation support.
    """

    def __init__(
        self,
        anchor: ProbeAnchor,
        color: QColor,
        dtype: str,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._anchor = anchor
        self._color = color
        self._dtype = dtype
        self._plot: Optional[BasePlot] = None
        self._removal_animation = None

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
        layout.setSpacing(4)

        # Header row with state indicator, identity label, and throttle indicator
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        # State indicator (16x16 pulsing/solid circle)
        self._state_indicator = ProbeStateIndicator()
        header.addWidget(self._state_indicator)

        # Identity label with colored styling
        self._identity_label = QLabel(self._anchor.identity_label())
        color_hex = self._color.name()
        self._identity_label.setStyleSheet(f"""
            QLabel {{
                color: {color_hex};
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        header.addWidget(self._identity_label)

        # Spacer
        header.addStretch()

        # Throttle indicator (hidden by default)
        self._throttle_label = QLabel("\u26a1")  # Lightning bolt
        self._throttle_label.setStyleSheet("""
            QLabel {
                color: #ffff00;
                font-size: 12px;
            }
        """)
        self._throttle_label.setToolTip("Data throttling active")
        self._throttle_label.hide()
        header.addWidget(self._throttle_label)

        layout.addLayout(header)

        # Create the appropriate plot widget
        self._plot = create_plot(self._anchor.symbol, self._dtype, self)
        layout.addWidget(self._plot)

        # Set minimum size
        self.setMinimumSize(300, 250)

    def update_data(self, value, dtype: str, shape=None, source_info: str = ""):
        """Update the plot with new data."""
        if self._plot:
            self._plot.update_data(value, dtype, shape, source_info)

    def set_state(self, state: ProbeState):
        """Update the state indicator."""
        self._state_indicator.set_state(state)

    def show_throttle_indicator(self, active: bool):
        """Show or hide the throttle icon."""
        if active:
            self._throttle_label.show()
        else:
            self._throttle_label.hide()

    def animate_removal(self, on_complete=None):
        """Fade out using ProbeAnimations, then call on_complete."""
        self._removal_animation = ProbeAnimations.fade_out(
            self, duration_ms=300, on_finished=on_complete
        )
        self._removal_animation.start()

    def show_invalid_click_feedback(self):
        """Flash state indicator red to show invalid click."""
        self._state_indicator.show_invalid_feedback()

    @property
    def anchor(self) -> ProbeAnchor:
        """Return the probe anchor."""
        return self._anchor

    @property
    def var_name(self) -> str:
        """Return variable name (for backwards compatibility)."""
        return self._anchor.symbol


class ProbePanelContainer(QScrollArea):
    """
    Scrollable container for multiple probe panels.

    Uses a grid layout to arrange panels.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._panels: Dict[ProbeAnchor, ProbePanel] = {}
        self._panels_by_name: Dict[str, ProbePanel] = {}  # For legacy access
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

    def create_panel(
        self,
        var_name: str,
        dtype: str,
        anchor: Optional[ProbeAnchor] = None,
        color: Optional[QColor] = None
    ) -> ProbePanel:
        """
        Create a new probe panel for a variable.

        Args:
            var_name: Variable name (used as fallback if no anchor)
            dtype: Data type string
            anchor: ProbeAnchor for the probe location
            color: Assigned color for the probe
        """
        # Create anchor if not provided (backwards compatibility)
        if anchor is None:
            anchor = ProbeAnchor(
                file="<unknown>",
                line=0,
                col=0,
                symbol=var_name
            )

        # Use default color if not provided
        if color is None:
            color = QColor('#00ffff')

        if anchor in self._panels:
            return self._panels[anchor]

        # Also check by var_name for legacy code
        if var_name in self._panels_by_name:
            return self._panels_by_name[var_name]

        # Hide placeholder
        self._placeholder.hide()

        # Create panel
        panel = ProbePanel(anchor, color, dtype, self._content)
        self._panels[anchor] = panel
        self._panels_by_name[var_name] = panel

        # Add to grid
        self._layout.addWidget(panel, self._next_row, self._next_col)

        # Advance position
        self._next_col += 1
        if self._next_col >= self._cols:
            self._next_col = 0
            self._next_row += 1

        return panel

    def remove_panel(self, var_name: str = None, anchor: ProbeAnchor = None):
        """Remove a probe panel by var_name or anchor."""
        panel = None

        if anchor is not None and anchor in self._panels:
            panel = self._panels.pop(anchor)
            # Remove from name index too
            for name, p in list(self._panels_by_name.items()):
                if p is panel:
                    del self._panels_by_name[name]
                    break
        elif var_name is not None and var_name in self._panels_by_name:
            panel = self._panels_by_name.pop(var_name)
            # Remove from anchor index too
            for a, p in list(self._panels.items()):
                if p is panel:
                    del self._panels[a]
                    break

        if panel is None:
            return

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

    def get_panel(self, var_name: str = None, anchor: ProbeAnchor = None) -> Optional[ProbePanel]:
        """Get a panel by variable name or anchor."""
        if anchor is not None:
            return self._panels.get(anchor)
        if var_name is not None:
            return self._panels_by_name.get(var_name)
        return None
