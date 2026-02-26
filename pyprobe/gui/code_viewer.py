"""
Code viewer widget with mouse tracking and click-to-probe functionality.

This widget provides:
- Syntax highlighted Python code display
- Mouse hover detection for variables
- Click-to-toggle probe activation
- Visual highlights for hovered and active probes
"""

from typing import Optional, Dict, Set
from PyQt6.QtWidgets import QPlainTextEdit, QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import (
    QTextCursor, QPainter, QColor, QPen, QBrush,
    QFont, QFontMetricsF, QTextCharFormat, QDrag
)

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.analysis.ast_locator import ASTLocator, VariableLocation
from pyprobe.gui.drag_helpers import encode_anchor_mime
from pyprobe.logging import get_logger

logger = get_logger(__name__)


class CodeViewer(QPlainTextEdit):
    """QPlainTextEdit with mouse tracking for variable probing.

    Signals:
        probe_requested: Emitted when user clicks on a variable to add probe
        probe_removed: Emitted when user clicks on an active probe to remove it
        hover_changed: Emitted when hovered variable changes (or None when leaving)
    """

    # Signals
    probe_requested = pyqtSignal(object)  # ProbeAnchor
    probe_removed = pyqtSignal(object)    # ProbeAnchor
    watch_probe_requested = pyqtSignal(object)  # ProbeAnchor (Alt+click for scalar watch)
    hover_changed = pyqtSignal(object)    # ProbeAnchor or None
    highlight_changed = pyqtSignal(object, bool)  # (ProbeAnchor, is_highlighted)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # File and AST state
        self._file_path: Optional[str] = None
        self._ast_locator: Optional[ASTLocator] = None

        # Probe state
        # anchor -> (color, ref_count) for visual highlights with reference counting
        # Ref count tracks how many probes (graphical + watch) are watching this symbol
        self._active_probes: Dict[ProbeAnchor, tuple] = {}  # tuple[QColor, int]
        # anchor -> count of graphical panels (supports multiple panels per anchor via Ctrl+click)
        self._graphical_probes: Dict[ProbeAnchor, int] = {}
        self._invalid_probes: Set[ProbeAnchor] = set()

        # Hover state
        self._hover_anchor: Optional[ProbeAnchor] = None
        self._hover_var_location: Optional[VariableLocation] = None
        self._hover_border_color = QColor("#00ffff")

        # M2.5: Drag state for signal overlay
        self._drag_start_pos: Optional[QPoint] = None
        self._drag_start_anchor: Optional[ProbeAnchor] = None

        self._setup_ui()

        from .theme.theme_manager import ThemeManager
        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.current)

    def _setup_ui(self) -> None:
        """Configure the code viewer UI."""
        # Enable mouse tracking for hover detection
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

        # Set read-only
        self.setReadOnly(True)

        # Disable word wrap - code should scroll horizontally, not wrap
        # This ensures col_start * char_width calculation remains valid
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # Configure default font before theme applies
        font = QFont("Menlo", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.setFont(font)

        # Configure cursor
        self.setCursorWidth(0)  # Hide text cursor

    def _apply_theme(self, theme) -> None:
        """Apply active theme colors and typography to the code viewer."""
        c = theme.colors
        mono_font = QFont()
        mono_font.setFamilies([
            "SF Mono", "JetBrains Mono", "Menlo", "Consolas", "Monaco", "monospace"
        ])
        mono_font.setPointSize(11)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        mono_font.setFixedPitch(True)
        self.setFont(mono_font)

        self._hover_border_color = QColor(c['accent_primary'])
        self._hover_border_color.setAlpha(110)

        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {c['bg_dark']};
                color: {c['text_primary']};
                border: none;
                selection-background-color: {c['accent_primary']};
                selection-color: {c['bg_darkest']};
            }}
        """)

    def load_file(self, file_path: str) -> bool:
        """Load a Python file into the viewer.

        Args:
            file_path: Absolute path to the Python file

        Returns:
            True if file was loaded successfully
        """
        import os
        # Resolve to absolute path to match tracer's code.co_filename
        file_path = os.path.abspath(file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
        except (IOError, OSError):
            return False

        self._file_path = file_path
        self.setPlainText(source)

        # Create AST locator for the source
        self._ast_locator = ASTLocator(source, filename=file_path)

        return True

    def reload_file(self) -> bool:
        """Reload the current file from disk.

        Returns:
            True if file was reloaded successfully
        """
        if self._file_path is None:
            return False
        return self.load_file(self._file_path)

    def set_probe_active(self, anchor: ProbeAnchor, color: QColor) -> None:
        """Mark a probe as active with the given color.

        Increments reference count if already active. Only removes highlight
        when all probe types (graphical, watch) have been removed.

        Args:
            anchor: The probe anchor to activate
            color: Color to use for highlighting
        """
        logger.debug(f"set_probe_active called with anchor: {anchor}")
        logger.debug(f"Before: _active_probes keys: {list(self._active_probes.keys())}")
        
        if anchor in self._active_probes:
            # Increment reference count, keep existing color
            existing_color, ref_count = self._active_probes[anchor]
            self._active_probes[anchor] = (existing_color, ref_count + 1)
            logger.debug(f"Incremented ref count for {anchor.symbol} to {ref_count + 1}")
        else:
            # New probe, start with ref count = 1
            self._active_probes[anchor] = (color, 1)
            logger.debug(f"Added new probe {anchor.symbol} with ref count 1")
            self.highlight_changed.emit(anchor, True)
        
        logger.debug(f"After: _active_probes keys: {list(self._active_probes.keys())}")
        self._invalid_probes.discard(anchor)
        self.viewport().update()

    def update_probe_color(self, anchor: ProbeAnchor, color: QColor) -> None:
        """Update the highlight color of an already-active probe without changing ref count."""
        if anchor in self._active_probes:
            _, ref_count = self._active_probes[anchor]
            self._active_probes[anchor] = (color, ref_count)
            self.viewport().update()

    def set_probe_invalid(self, anchor: ProbeAnchor) -> None:
        """Mark a probe as invalid (e.g., line changed).

        Args:
            anchor: The probe anchor to mark as invalid
        """
        self._invalid_probes.add(anchor)
        self.viewport().update()

    def remove_probe(self, anchor: ProbeAnchor) -> None:
        """Decrement reference count and remove probe highlight when count reaches 0.

        Args:
            anchor: The probe anchor to remove
        """
        logger.debug(f"remove_probe called with anchor: {anchor}")
        logger.debug(f"Before: _active_probes keys: {list(self._active_probes.keys())}")
        
        if anchor in self._active_probes:
            color, ref_count = self._active_probes[anchor]
            if ref_count > 1:
                # Decrement reference count, keep highlight
                self._active_probes[anchor] = (color, ref_count - 1)
                logger.debug(f"Decremented ref count for {anchor.symbol} to {ref_count - 1}")
            else:
                # Last reference, remove highlight entirely
                self._active_probes.pop(anchor, None)
                self._graphical_probes.pop(anchor, None)
                self._invalid_probes.discard(anchor)
                logger.debug(f"Removed last reference for {anchor.symbol}")
                self.highlight_changed.emit(anchor, False)
        else:
            logger.debug(f"remove_probe called for unknown anchor: {anchor}")
        
        logger.debug(f"After: _active_probes keys: {list(self._active_probes.keys())}")
        self.viewport().update()

    def set_probe_graphical(self, anchor: ProbeAnchor) -> None:
        """Mark a probe as having a graphical panel.

        Increments the graphical panel count for this anchor.

        Args:
            anchor: The probe anchor with a panel
        """
        self._graphical_probes[anchor] = self._graphical_probes.get(anchor, 0) + 1
        logger.debug(f"set_probe_graphical: {anchor.symbol} now has {self._graphical_probes[anchor]} panel(s)")

    def unset_probe_graphical(self, anchor: ProbeAnchor) -> None:
        """Mark a probe as having one fewer graphical panel.

        Decrements the graphical panel count for this anchor.
        Removes the anchor from tracking when count reaches 0.

        Args:
            anchor: The probe anchor to decrement
        """
        if anchor in self._graphical_probes:
            self._graphical_probes[anchor] -= 1
            logger.debug(f"unset_probe_graphical: {anchor.symbol} now has {self._graphical_probes[anchor]} panel(s)")
            if self._graphical_probes[anchor] <= 0:
                del self._graphical_probes[anchor]
                logger.debug(f"unset_probe_graphical: {anchor.symbol} removed from graphical probes")

    def has_graphical_probe(self, anchor: ProbeAnchor) -> bool:
        """Check if an anchor has at least one graphical panel.

        Args:
            anchor: The probe anchor to check

        Returns:
            True if anchor has at least one graphical panel
        """
        return self._graphical_probes.get(anchor, 0) > 0

    def clear_all_probes(self) -> None:
        """Remove all active probes."""
        self._active_probes.clear()
        self._graphical_probes.clear()
        self._invalid_probes.clear()
        self.viewport().update()

    def _get_anchor_at_position(self, pos: QPoint) -> Optional[ProbeAnchor]:
        """Get the ProbeAnchor at the given widget position.

        Args:
            pos: Widget-relative position (from mouse event)

        Returns:
            ProbeAnchor if a variable is at position, None otherwise
        """
        if self._ast_locator is None or self._file_path is None:
            return None

        # Get text cursor at position
        cursor = self.cursorForPosition(pos)
        block = cursor.block()

        # Get line number (1-indexed)
        line = block.blockNumber() + 1

        # Get column position within block
        col = cursor.positionInBlock()

        # Find nearest variable
        var_loc = self._ast_locator.get_nearest_variable(line, col)
        if var_loc is None:
            return None

        # Get enclosing function
        func_name = self._ast_locator.get_enclosing_function(line) or ""

        # Create and return anchor
        return ProbeAnchor(
            file=self._file_path,
            line=var_loc.line,
            col=var_loc.col_start,
            symbol=var_loc.name,
            func=func_name,
            is_assignment=var_loc.is_lhs,
        )

    def _get_var_location_at_position(self, pos: QPoint) -> Optional[VariableLocation]:
        """Get the VariableLocation at the given widget position."""
        if self._ast_locator is None:
            return None

        cursor = self.cursorForPosition(pos)
        block = cursor.block()
        line = block.blockNumber() + 1
        col = cursor.positionInBlock()

        return self._ast_locator.get_nearest_variable(line, col)

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse movement for hover detection and drag initiation."""
        super().mouseMoveEvent(event)

        # M2.5: Check for drag initiation
        if self._drag_start_pos is not None and self._drag_start_anchor is not None:
            distance = (event.pos() - self._drag_start_pos).manhattanLength()
            if distance > 10:
                logger.debug(f"mouseMoveEvent: Threshold exceeded (distance={distance}), initiating drag")
                self._start_drag()
                self._drag_start_pos = None
                self._drag_start_anchor = None
                return

        # Get anchor at current position
        new_anchor = self._get_anchor_at_position(event.pos())
        new_var_loc = self._get_var_location_at_position(event.pos())

        # Check if hover changed
        if new_anchor != self._hover_anchor:
            self._hover_anchor = new_anchor
            self._hover_var_location = new_var_loc
            self.hover_changed.emit(new_anchor)
            self.viewport().update()

    def mousePressEvent(self, event) -> None:
        """Handle mouse press - record position for potential drag or click."""
        if event.button() == Qt.MouseButton.LeftButton:
            anchor = self._get_anchor_at_position(event.pos())
            if anchor is not None:
                # Record drag start position and anchor for potential drag or click
                self._drag_start_pos = event.pos()
                self._drag_start_anchor = anchor
                logger.debug(f"mousePressEvent: Recorded start for {anchor.symbol}")
                # Accept the event to prevent text selection
                event.accept()
                return  # Don't call super() - prevent QPlainTextEdit from starting text selection
            else:
                self._drag_start_pos = None
                self._drag_start_anchor = None

        super().mousePressEvent(event)

    def leaveEvent(self, event) -> None:
        """Handle mouse leaving the widget."""
        super().leaveEvent(event)
        self._drag_start_pos = None
        self._drag_start_anchor = None

        if self._hover_anchor is not None:
            self._hover_anchor = None
            self._hover_var_location = None
            self.hover_changed.emit(None)
            self.viewport().update()

    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release - toggle probe if no drag occurred."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Only toggle probe if we started on an anchor and didn't drag
            if self._drag_start_anchor is not None and self._drag_start_pos is not None:
                distance = (event.pos() - self._drag_start_pos).manhattanLength()
                # Check if we stayed in roughly the same position (not a drag)
                if distance <= 10:
                    anchor = self._drag_start_anchor
                    has_graphical_panel = self.has_graphical_probe(anchor)
                    is_highlighted = anchor in self._active_probes
                    # Use Shift for duplicate probe - works cross-platform without conflicts
                    is_shift_held = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
                    logger.debug(f"mouseReleaseEvent: Click completed on {anchor.symbol}, has_panel={has_graphical_panel}, is_highlighted={is_highlighted}, shift={is_shift_held}")

                    # Check for Alt modifier -> watch window toggle
                    if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                        self.watch_probe_requested.emit(anchor)
                    elif is_shift_held and has_graphical_panel:
                        # Shift+click on graphical probe -> create another panel (duplicate)
                        logger.debug(f"Shift+click: creating duplicate probe for {anchor.symbol}")
                        self.probe_requested.emit(anchor)
                    elif has_graphical_panel:
                        # Regular click on graphical probe -> remove it
                        self.probe_removed.emit(anchor)
                    else:
                        # Regular click on non-graphical symbol -> create graphical probe
                        # This includes: unhighlighted symbols AND watch-only symbols
                        self.probe_requested.emit(anchor)
                # else: distance > 10, was a drag, don't toggle
            # else: no drag_start state
        
        self._drag_start_pos = None
        self._drag_start_anchor = None
        super().mouseReleaseEvent(event)

    def _start_drag(self) -> None:
        """Initiate drag-and-drop for signal overlay."""
        # Use _drag_start_anchor instead of _hover_anchor
        anchor = self._drag_start_anchor
        if anchor is None:
            return

        logger.debug(f"_start_drag: Starting drag for {anchor.symbol}")
        
        # Clear hover state before drag to prevent paint conflicts
        self._hover_anchor = None
        self._hover_var_location = None
        
        mime_data = encode_anchor_mime(
            file=anchor.file,
            line=anchor.line,
            col=anchor.col,
            symbol=anchor.symbol,
            func=anchor.func or "",
            is_assignment=anchor.is_assignment,
        )
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        result = drag.exec(Qt.DropAction.CopyAction)

    def paintEvent(self, event) -> None:
        """Custom paint to draw variable highlights."""
        # Let the base class paint text first
        super().paintEvent(event)

        # Draw highlights on top - check if we can acquire a painter
        painter = QPainter()
        if not painter.begin(self.viewport()):
            # Another painter is active, skip custom drawing this frame
            return
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw active probe highlights
        for anchor, (color, ref_count) in self._active_probes.items():
            is_invalid = anchor in self._invalid_probes
            self._draw_probe_highlight(painter, anchor, color, is_invalid)

        # Draw hover highlight (if not an active probe)
        if self._hover_anchor is not None and self._hover_var_location is not None:
            if self._hover_anchor not in self._active_probes:
                self._draw_hover_highlight(painter, self._hover_var_location)

        painter.end()

    def _draw_probe_highlight(
        self,
        painter: QPainter,
        anchor: ProbeAnchor,
        color: QColor,
        is_invalid: bool
    ) -> None:
        """Draw highlight for an active probe.

        Args:
            painter: QPainter to draw with
            anchor: The probe anchor
            color: Color for the highlight
            is_invalid: Whether the probe is invalid
        """
        # Find the variable location in current AST
        if self._ast_locator is None:
            return

        # Get all variables on the anchor's line
        vars_on_line = self._ast_locator.get_all_variables_on_line(anchor.line)
        var_loc = None
        for v in vars_on_line:
            if v.name == anchor.symbol and v.col_start == anchor.col:
                var_loc = v
                break

        if var_loc is None:
            # Variable not found at exact location, try by name
            for v in vars_on_line:
                if v.name == anchor.symbol:
                    var_loc = v
                    break

        if var_loc is None:
            return

        rect = self._get_rect_for_variable(var_loc)
        if rect is None:
            return

        # Set up colors
        if is_invalid:
            # Gray out invalid probes
            fill_color = QColor(100, 100, 100, 80)
            border_color = QColor(100, 100, 100)
        else:
            fill_color = QColor(color)
            fill_color.setAlpha(60)
            border_color = color

        # Draw filled rectangle with border
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QBrush(fill_color))
        painter.drawRoundedRect(rect, 2, 2)

    def _draw_hover_highlight(
        self,
        painter: QPainter,
        var_loc: VariableLocation
    ) -> None:
        """Draw subtle hover highlight for a variable.

        Args:
            painter: QPainter to draw with
            var_loc: The variable location to highlight
        """
        rect = self._get_rect_for_variable(var_loc)
        if rect is None:
            return

        painter.setPen(QPen(self._hover_border_color, 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 2, 2)

    def _get_rect_for_variable(self, var_loc: VariableLocation):
        """Calculate the screen rectangle for a variable location.

        Args:
            var_loc: The variable location

        Returns:
            QRectF for the variable, or None if not visible
        """
        # Get the block for this line
        block = self.document().findBlockByLineNumber(var_loc.line - 1)
        if not block.isValid():
            return None

        # Get block geometry
        block_geom = self.blockBoundingGeometry(block)
        content_offset = self.contentOffset()
        doc_margin = self.document().documentMargin()

        # Calculate character width using font metrics
        fm = QFontMetricsF(self.font())
        char_width = fm.horizontalAdvance('m')  # Monospace, so any char works

        # Calculate rectangle (doc_margin accounts for QTextDocument padding)
        x = block_geom.x() + content_offset.x() + doc_margin + (var_loc.col_start * char_width)
        y = block_geom.y() + content_offset.y()
        width = (var_loc.col_end - var_loc.col_start) * char_width
        height = block_geom.height()

        from PyQt6.QtCore import QRectF
        return QRectF(x, y, width, height)

    @property
    def file_path(self) -> Optional[str]:
        """Return the currently loaded file path."""
        return self._file_path

    @property
    def ast_locator(self) -> Optional[ASTLocator]:
        """Return the AST locator for the current file."""
        return self._ast_locator

    def open_file_entries(self) -> list:
        """Return a list of OpenFileEntry for the currently loaded file."""
        if self._file_path is None:
            return []
        from pyprobe.report.report_model import OpenFileEntry
        return [OpenFileEntry(
            path=self._file_path,
            is_probed=len(self._active_probes) > 0,
            is_executed=False,
            has_unsaved=self.document().isModified(),
            contents=self.toPlainText(),
        )]
