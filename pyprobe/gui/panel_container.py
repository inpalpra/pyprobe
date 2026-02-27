"""
Container widget for probe panels with grid layout.
"""

from typing import Dict, Optional, List
from PyQt6.QtWidgets import (
    QWidget, QScrollArea, QGridLayout, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from pyprobe.logging import get_logger
logger = get_logger(__name__)

from ..core.anchor import ProbeAnchor
from ..core.window_id_manager import WindowIDManager
from ..core.trace_reference_manager import TraceReferenceManager
from .probe_panel import ProbePanel


class ProbePanelContainer(QScrollArea):
    """
    Scrollable container for multiple probe panels.

    Uses a grid layout to arrange panels.
    """

    # Emitted before a panel is removed, so controllers can clean up overlays etc.
    panel_closing = pyqtSignal(object)  # ProbePanel

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Supports multiple panels per anchor via Ctrl+click
        self._panels: Dict[ProbeAnchor, List[ProbePanel]] = {}
        self._panels_by_name: Dict[str, ProbePanel] = {}  # For legacy access
        self._parked_panels: set = set()  # Track parked panel anchors
        self._wid_manager = WindowIDManager()

        # M2.5: Layout manager and focus manager
        from .layout_manager import LayoutManager
        from .focus_manager import FocusManager
        self._layout_manager = LayoutManager(self)
        self._focus_manager = FocusManager(self)

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
        
        # Ensure equal column width
        for c in range(self._cols):
            self._layout.setColumnStretch(c, 1)

    def create_panel(
        self,
        var_name: str,
        dtype: str,
        anchor: Optional[ProbeAnchor] = None,
        color: Optional[QColor] = None,
        trace_id: str = ""
    ) -> ProbePanel:
        """
        Create a new probe panel for a variable.

        Args:
            var_name: Variable name (used as fallback if no anchor)
            dtype: Data type string
            anchor: ProbeAnchor for the probe location
            color: Assigned color for the probe
            trace_id: Trace ID (e.g., tr0)
        """
        logger.debug(f"create_panel called: var_name={var_name}, anchor={anchor}")
        logger.debug(f"  _panels keys: {list(self._panels.keys())}")
        logger.debug(f"  _panels_by_name keys: {list(self._panels_by_name.keys())}")

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

        # Only check by var_name for legacy code (when no real anchor provided)
        # When a real anchor IS provided, we always create a new panel
        # (Ctrl+click can create multiple panels for same anchor)
        if anchor.file == "<unknown>" and var_name in self._panels_by_name:
            logger.debug(f"  Returning existing panel from _panels_by_name for var_name={var_name}")
            return self._panels_by_name[var_name]

        # Hide placeholder
        self._placeholder.hide()

        # Allocate window ID
        window_id = self._wid_manager.allocate()

        # Create panel
        panel = ProbePanel(anchor, color, dtype, trace_id, window_id, self._content)
        
        # Track reference
        if trace_id:
            TraceReferenceManager.instance().add_reference(trace_id, window_id)

        if anchor not in self._panels:
            self._panels[anchor] = []
        self._panels[anchor].append(panel)
        # Only add to _panels_by_name for legacy (anchor-less) panels
        if anchor.file == "<unknown>":
            self._panels_by_name[var_name] = panel
        logger.debug(f"  Created new panel, added to _panels list (now {len(self._panels[anchor])} panels for this anchor)")

        # M2.5: Connect maximize/park signals and register with focus manager
        panel.maximize_requested.connect(lambda p=panel: self._layout_manager.toggle_maximize(p))
        panel.close_requested.connect(lambda p=panel: self.remove_panel(panel=p))
        self._focus_manager.register_panel(panel)

        # Add to grid via relayout to handle spanning logic
        self._relayout_panels()

        return panel

    def remove_panel(self, var_name: str = None, anchor: ProbeAnchor = None, panel: ProbePanel = None):
        """Remove a probe panel by var_name, anchor, or panel reference.

        If panel is provided, removes that specific panel.
        If anchor is provided, removes the last panel for that anchor.
        If var_name is provided, removes the panel by name (legacy).
        """
        logger.debug(f"remove_panel called: var_name={var_name}, anchor={anchor}, panel={panel}")
        logger.debug(f"  Before: _panels keys: {list(self._panels.keys())}")
        logger.debug(f"  Before: _panels_by_name keys: {list(self._panels_by_name.keys())}")

        target_panel = None

        # Option 1: Panel reference provided directly
        if panel is not None:
            target_panel = panel
            # Find and remove from _panels
            for a, panel_list in list(self._panels.items()):
                if panel in panel_list:
                    panel_list.remove(panel)
                    logger.debug(f"  Removed panel from _panels[{a.symbol}] (now {len(panel_list)} remaining)")
                    if not panel_list:
                        del self._panels[a]
                        logger.debug(f"  Deleted empty list for anchor {a.symbol}")
                    break
            # Remove from name index too
            for name, p in list(self._panels_by_name.items()):
                if p is panel:
                    del self._panels_by_name[name]
                    logger.debug(f"  Also removed from _panels_by_name: {name}")
                    break

        # Option 2: Anchor provided - remove last panel from list
        elif anchor is not None and anchor in self._panels:
            panel_list = self._panels[anchor]
            if panel_list:
                target_panel = panel_list.pop()
                logger.debug(f"  Popped last panel from _panels for anchor (now {len(panel_list)} remaining)")
                if not panel_list:
                    del self._panels[anchor]
                    logger.debug(f"  Deleted empty list for anchor")
            # Remove from name index too
            if target_panel is not None:
                for name, p in list(self._panels_by_name.items()):
                    if p is target_panel:
                        del self._panels_by_name[name]
                        logger.debug(f"  Also removed from _panels_by_name: {name}")
                        break

        # Option 3: var_name provided (legacy)
        elif var_name is not None and var_name in self._panels_by_name:
            target_panel = self._panels_by_name.pop(var_name)
            logger.debug(f"  Popped panel from _panels_by_name for var_name")
            # Remove from anchor index too
            for a, panel_list in list(self._panels.items()):
                if target_panel in panel_list:
                    panel_list.remove(target_panel)
                    if not panel_list:
                        del self._panels[a]
                    logger.debug(f"  Also removed from _panels")
                    break

        if target_panel is None:
            logger.debug(f"  No panel found to remove")
            return

        # Notify controllers before marking as closing (so they can clean up overlays etc.)
        self.panel_closing.emit(target_panel)

        # Mark as closing to prevent redundant removal calls from signals
        if hasattr(target_panel, "is_closing"):
            target_panel.is_closing = True

        logger.debug(f"  After: _panels keys: {list(self._panels.keys())}")
        logger.debug(f"  After: _panels_by_name keys: {list(self._panels_by_name.keys())}")

        # M2.5: Unregister from focus manager
        self._focus_manager.unregister_panel(target_panel)

        # Release window ID
        wid = None
        if hasattr(target_panel, "window_id"):
            wid = target_panel.window_id
            self._wid_manager.release(wid)

        self._layout.removeWidget(target_panel)
        target_panel.deleteLater()

        # Notify reference manager AFTER deleteLater so sip.isdeleted(target_panel) is True
        if wid:
            TraceReferenceManager.instance().cleanup_window(wid)

        # Re-layout remaining panels
        self._relayout_panels()

        # Show placeholder if empty
        if not self._panels:
            self._placeholder.show()

    def _relayout_panels(self):
        """Re-layout panels after changes."""
        # Remove all panels from layout
        # (We iterate a copy of keys or values if needed, but removeWidget is safe)
        for i in reversed(range(self._layout.count())):
            item = self._layout.itemAt(i)
            if item.widget() and item.widget() != self._placeholder:
                self._layout.removeWidget(item.widget())

        # Only layout non-parked panels (flatten the list of lists)
        panels = []
        for anchor, panel_list in self._panels.items():
            if anchor not in self._parked_panels:
                panels.extend(panel_list)
        if not panels:
            return

        self._next_row = 0
        self._next_col = 0
        
        # If only one panel, span full width
        if len(panels) == 1:
            self._layout.addWidget(panels[0], 0, 0, 1, self._cols)
            self._next_row = 1
            self._next_col = 0
        else:
            # Otherwise grid layout
            # If odd number of panels, last one gets full width
            last_idx = len(panels) - 1
            for i, panel in enumerate(panels):
                is_last = (i == last_idx)
                is_odd_count = (len(panels) % 2 == 1)
                
                if is_last and is_odd_count:
                    # Last panel with odd count: span full width
                    self._layout.addWidget(panel, self._next_row, 0, 1, self._cols)
                    self._next_row += 1
                    self._next_col = 0
                else:
                    self._layout.addWidget(panel, self._next_row, self._next_col)
                    self._next_col += 1
                    if self._next_col >= self._cols:
                        self._next_col = 0
                        self._next_row += 1

        # Calculate total number of rows used
        total_rows = self._next_row
        if self._next_col > 0:
            total_rows += 1

        # Set uniform row stretch for all used rows, reset for others
        # to ensure aspect-locked plots don't steal vertical space.
        for r in range(self._layout.rowCount()):
            if r < total_rows:
                self._layout.setRowStretch(r, 1)
            else:
                self._layout.setRowStretch(r, 0)

    def get_panel(self, var_name: str = None, anchor: ProbeAnchor = None) -> Optional[ProbePanel]:
        """Get the first panel by variable name or anchor (for backwards compatibility)."""
        if anchor is not None:
            panel_list = self._panels.get(anchor)
            return panel_list[0] if panel_list else None
        if var_name is not None:
            return self._panels_by_name.get(var_name)
        return None

    def get_all_panels(self, anchor: ProbeAnchor = None) -> List[ProbePanel]:
        """Get all panels for an anchor, or all panels if anchor is None."""
        if anchor is not None:
            return list(self._panels.get(anchor, []))
        # Return all panels flattened
        all_panels = []
        for panel_list in self._panels.values():
            all_panels.extend(panel_list)
        return all_panels

    def relayout(self) -> None:
        """Trigger a relayout of visible panels (public API for park/restore)."""
        self._relayout_panels()

    def park_panel(self, anchor: ProbeAnchor) -> None:
        """Mark a panel as parked (excluded from layout)."""
        self._parked_panels.add(anchor)
        self._relayout_panels()

    def unpark_panel(self, anchor: ProbeAnchor) -> None:
        """Mark a panel as unparked (included in layout)."""
        self._parked_panels.discard(anchor)
        self._relayout_panels()

    # === M1 CONVENIENCE METHODS ===

    def create_probe_panel(self, anchor: ProbeAnchor, color: QColor, trace_id: str = "") -> ProbePanel:
        """Create a probe panel for an anchor (M1 API)."""
        return self.create_panel(
            var_name=anchor.symbol,
            dtype='unknown',
            anchor=anchor,
            color=color,
            trace_id=trace_id
        )

    def remove_probe_panel(self, anchor: ProbeAnchor = None, panel: ProbePanel = None):
        """Remove a probe panel by anchor or panel reference (M1 API)."""
        self.remove_panel(anchor=anchor, panel=panel)

    # === M2.5: Tab navigation ===

    def keyPressEvent(self, event) -> None:
        """Handle Tab to cycle focus between panels."""
        if event.key() == Qt.Key.Key_Tab:
            self._focus_manager.focus_next()
            # Actually give Qt focus to the panel
            panel = self._focus_manager.focused_panel
            if panel is not None:
                panel.setFocus()
            event.accept()
        else:
            super().keyPressEvent(event)

    @property
    def layout_manager(self):
        """Access the layout manager."""
        return self._layout_manager

    @property
    def focus_manager(self):
        """Access the focus manager."""
        return self._focus_manager

    def graph_widget_entries(self, registry) -> list:
        """Return a list of GraphWidgetEntry for each probe panel."""
        entries = []
        for anchor, panel_list in self._panels.items():
            for panel in panel_list:
                is_docked = anchor not in self._parked_panels
                entries.append(panel.get_report_entry(registry, is_docked))
        return entries
