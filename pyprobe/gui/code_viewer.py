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
    QFont, QFontMetricsF, QTextCharFormat
)

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.analysis.ast_locator import ASTLocator, VariableLocation
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
    hover_changed = pyqtSignal(object)    # ProbeAnchor or None

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # File and AST state
        self._file_path: Optional[str] = None
        self._ast_locator: Optional[ASTLocator] = None

        # Probe state
        self._active_probes: Dict[ProbeAnchor, QColor] = {}  # anchor -> color
        self._invalid_probes: Set[ProbeAnchor] = set()

        # Hover state
        self._hover_anchor: Optional[ProbeAnchor] = None
        self._hover_var_location: Optional[VariableLocation] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configure the code viewer UI."""
        # Enable mouse tracking for hover detection
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

        # Set read-only
        self.setReadOnly(True)

        # Configure font - Menlo 11pt monospace
        font = QFont("Menlo", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.setFont(font)

        # Dark theme colors
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0d0d0d;
                color: #ffffff;
                border: none;
                selection-background-color: #00ffff;
                selection-color: #0d0d0d;
            }
        """)

        # Configure cursor
        self.setCursorWidth(0)  # Hide text cursor

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

        Args:
            anchor: The probe anchor to activate
            color: Color to use for highlighting
        """
        logger.debug(f"set_probe_active called with anchor: {anchor}")
        logger.debug(f"Before: _active_probes keys: {list(self._active_probes.keys())}")
        self._active_probes[anchor] = color
        logger.debug(f"After: _active_probes keys: {list(self._active_probes.keys())}")
        self._invalid_probes.discard(anchor)
        self.viewport().update()

    def set_probe_invalid(self, anchor: ProbeAnchor) -> None:
        """Mark a probe as invalid (e.g., line changed).

        Args:
            anchor: The probe anchor to mark as invalid
        """
        self._invalid_probes.add(anchor)
        self.viewport().update()

    def remove_probe(self, anchor: ProbeAnchor) -> None:
        """Remove a probe from the active set.

        Args:
            anchor: The probe anchor to remove
        """
        logger.debug(f"remove_probe called with anchor: {anchor}")
        logger.debug(f"Before: _active_probes keys: {list(self._active_probes.keys())}")
        self._active_probes.pop(anchor, None)
        logger.debug(f"After: _active_probes keys: {list(self._active_probes.keys())}")
        self._invalid_probes.discard(anchor)
        self.viewport().update()

    def clear_all_probes(self) -> None:
        """Remove all active probes."""
        self._active_probes.clear()
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
        
        # Check if symbol is probeable
        if not self._ast_locator.is_probeable(var_loc):
            logger.debug(f"_get_anchor_at_position: symbol not probeable: {var_loc}")
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
        """Handle mouse movement for hover detection."""
        super().mouseMoveEvent(event)

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
        """Handle mouse clicks for probe toggle."""
        if event.button() == Qt.MouseButton.LeftButton:
            anchor = self._get_anchor_at_position(event.pos())
            logger.debug(f"mousePressEvent: Click at pos {event.pos()}")
            logger.debug(f"mousePressEvent: anchor at position: {anchor}")
            logger.debug(f"mousePressEvent: _active_probes keys: {list(self._active_probes.keys())}")

            if anchor is not None:
                is_active = anchor in self._active_probes
                logger.debug(f"mousePressEvent: anchor in _active_probes: {is_active}")
                # Check if clicking on an active probe
                if is_active:
                    logger.debug(f"mousePressEvent: Emitting probe_removed for {anchor}")
                    self.probe_removed.emit(anchor)
                else:
                    logger.debug(f"mousePressEvent: Emitting probe_requested for {anchor}")
                    self.probe_requested.emit(anchor)

        super().mousePressEvent(event)

    def leaveEvent(self, event) -> None:
        """Handle mouse leaving the widget."""
        super().leaveEvent(event)

        if self._hover_anchor is not None:
            self._hover_anchor = None
            self._hover_var_location = None
            self.hover_changed.emit(None)
            self.viewport().update()

    def paintEvent(self, event) -> None:
        """Custom paint to draw variable highlights."""
        # Let the base class paint text first
        super().paintEvent(event)

        # Draw highlights on top
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw active probe highlights
        for anchor, color in self._active_probes.items():
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
        # Only draw hover if probeable
        if self._ast_locator is not None and not self._ast_locator.is_probeable(var_loc):
            return  # No visual feedback for non-probeable
        
        rect = self._get_rect_for_variable(var_loc)
        if rect is None:
            return

        # Subtle cyan border for hover
        hover_color = QColor("#00ffff")
        hover_color.setAlpha(100)

        painter.setPen(QPen(hover_color, 1, Qt.PenStyle.DashLine))
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

        # Calculate character width using font metrics
        fm = QFontMetricsF(self.font())
        char_width = fm.horizontalAdvance('m')  # Monospace, so any char works

        # Calculate rectangle
        x = block_geom.x() + content_offset.x() + (var_loc.col_start * char_width)
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
