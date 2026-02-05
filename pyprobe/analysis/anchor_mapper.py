"""Anchor mapping for preserving probe locations across file edits."""
import difflib
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.analysis.ast_locator import ASTLocator


@dataclass
class AnchorMapping:
    """Result of mapping an anchor from old source to new source."""
    old_anchor: ProbeAnchor
    new_anchor: Optional[ProbeAnchor]  # None if invalid
    confidence: float  # 0.0 to 1.0


class AnchorMapper:
    """Maps probe anchors from old source to new source after file edits.

    Mapping Strategy (4-tier confidence):
    - 1.0 (Exact): Same (line, col, symbol, func) exists after line shift
    - 0.7 (Near): Same (symbol, func) exists nearby (within same function)
    - 0.4 (Weak): Only symbol exists anywhere in file
    - 0.0 (Invalid): Cannot find symbol at all
    """

    def __init__(self, old_source: str, new_source: str, filepath: str):
        """Initialize mapper with old and new source code.

        Args:
            old_source: The original source code
            new_source: The modified source code
            filepath: The file path (for creating new anchors)
        """
        self._old_source = old_source
        self._new_source = new_source
        self._filepath = filepath

        # Parse both sources
        self._old_locator = ASTLocator(old_source, filepath)
        self._new_locator = ASTLocator(new_source, filepath)

        # Compute line mapping from old to new
        self._line_map = self._compute_line_map()

    def _compute_line_map(self) -> Dict[int, int]:
        """Use difflib to map old line numbers to new line numbers.

        Returns:
            Dict mapping old line number (1-indexed) to new line number (1-indexed).
            Only includes lines that exist in both versions (unchanged lines).
        """
        old_lines = self._old_source.splitlines()
        new_lines = self._new_source.splitlines()

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        line_map: Dict[int, int] = {}

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Lines are identical - map each old line to corresponding new line
                for offset in range(i2 - i1):
                    old_line = i1 + offset + 1  # 1-indexed
                    new_line = j1 + offset + 1  # 1-indexed
                    line_map[old_line] = new_line

        return line_map

    def map_anchor(self, anchor: ProbeAnchor) -> AnchorMapping:
        """Map a single anchor to its new location.

        Args:
            anchor: The probe anchor to map

        Returns:
            AnchorMapping with new_anchor (or None) and confidence score
        """
        # Tier 1: Exact match after line shift (confidence 1.0)
        exact_result = self._try_exact_match(anchor)
        if exact_result is not None:
            return AnchorMapping(anchor, exact_result, 1.0)

        # Tier 2: Symbol in same function nearby (confidence 0.7)
        func_result = self._find_symbol_in_function(anchor)
        if func_result is not None:
            return AnchorMapping(anchor, func_result, 0.7)

        # Tier 3: Symbol exists anywhere (confidence 0.4)
        anywhere_result = self._find_symbol_anywhere(anchor)
        if anywhere_result is not None:
            return AnchorMapping(anchor, anywhere_result, 0.4)

        # Tier 4: Invalid - symbol not found (confidence 0.0)
        return AnchorMapping(anchor, None, 0.0)

    def _try_exact_match(self, anchor: ProbeAnchor) -> Optional[ProbeAnchor]:
        """Try to find exact match at mapped line position.

        Returns new anchor if the same symbol exists at the same column
        on the mapped line within the same function.
        """
        # Check if old line maps to a new line
        if anchor.line not in self._line_map:
            return None

        new_line = self._line_map[anchor.line]

        # Check if same symbol exists at same column on new line
        var_name = self._new_locator.get_var_at_cursor(new_line, anchor.col)
        if var_name != anchor.symbol:
            return None

        # Verify same enclosing function
        new_func = self._new_locator.get_enclosing_function(new_line) or ""
        if new_func != anchor.func:
            return None

        # Exact match found
        return ProbeAnchor(
            file=self._filepath,
            line=new_line,
            col=anchor.col,
            symbol=anchor.symbol,
            func=new_func,
        )

    def _find_symbol_in_function(self, anchor: ProbeAnchor) -> Optional[ProbeAnchor]:
        """Find the same symbol within the same function.

        Searches for the symbol in the new source, preferring occurrences
        within the same function.
        """
        if not anchor.func:
            # No function context to search within
            return None

        # Find all variables in new source
        new_lines = self._new_source.splitlines()
        for line_num in range(1, len(new_lines) + 1):
            # Check if this line is in the same function
            func_name = self._new_locator.get_enclosing_function(line_num)
            if func_name != anchor.func:
                continue

            # Check for symbol on this line
            vars_on_line = self._new_locator.get_all_variables_on_line(line_num)
            for var in vars_on_line:
                if var.name == anchor.symbol:
                    return ProbeAnchor(
                        file=self._filepath,
                        line=line_num,
                        col=var.col_start,
                        symbol=anchor.symbol,
                        func=func_name or "",
                    )

        return None

    def _find_symbol_anywhere(self, anchor: ProbeAnchor) -> Optional[ProbeAnchor]:
        """Find first occurrence of symbol anywhere in new source."""
        new_lines = self._new_source.splitlines()
        for line_num in range(1, len(new_lines) + 1):
            vars_on_line = self._new_locator.get_all_variables_on_line(line_num)
            for var in vars_on_line:
                if var.name == anchor.symbol:
                    func_name = self._new_locator.get_enclosing_function(line_num)
                    return ProbeAnchor(
                        file=self._filepath,
                        line=line_num,
                        col=var.col_start,
                        symbol=anchor.symbol,
                        func=func_name or "",
                    )

        return None

    def map_all(self, anchors: List[ProbeAnchor]) -> List[AnchorMapping]:
        """Map all anchors and return list of mappings.

        Args:
            anchors: List of probe anchors to map

        Returns:
            List of AnchorMapping results
        """
        return [self.map_anchor(anchor) for anchor in anchors]

    def get_invalidated(self, anchors: List[ProbeAnchor]) -> Set[ProbeAnchor]:
        """Return set of anchors that could not be mapped (invalid).

        Args:
            anchors: List of probe anchors to check

        Returns:
            Set of anchors with confidence 0.0 (no new_anchor)
        """
        invalid: Set[ProbeAnchor] = set()
        for anchor in anchors:
            mapping = self.map_anchor(anchor)
            if mapping.new_anchor is None:
                invalid.add(anchor)
        return invalid

    def get_valid_mappings(self, anchors: List[ProbeAnchor]) -> Dict[ProbeAnchor, ProbeAnchor]:
        """Return dict of old anchor -> new anchor for valid mappings.

        Args:
            anchors: List of probe anchors to map

        Returns:
            Dict mapping old anchors to their new locations
            (only includes anchors with confidence > 0.0)
        """
        valid: Dict[ProbeAnchor, ProbeAnchor] = {}
        for anchor in anchors:
            mapping = self.map_anchor(anchor)
            if mapping.new_anchor is not None:
                valid[mapping.old_anchor] = mapping.new_anchor
        return valid
