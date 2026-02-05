# Plan 1: AST Locator

**Focus:** Pure Python AST analysis - map cursor position to variable names.

**Branch:** `m1/ast-locator`

**Dependencies:** Plan 0 (ProbeAnchor)

**Complexity:** Medium (M)

---

## Files to Create

### `pyprobe/analysis/__init__.py`
```python
"""Source code analysis utilities."""
from .ast_locator import ASTLocator

__all__ = ['ASTLocator']
```

### `pyprobe/analysis/ast_locator.py`
```python
"""AST-based source code analysis for variable location."""
import ast
from typing import Optional, List, Tuple, Set
from dataclasses import dataclass

@dataclass
class VariableLocation:
    """Location of a variable in source code."""
    name: str
    line: int       # 1-indexed
    col_start: int  # 0-indexed
    col_end: int    # 0-indexed, exclusive
    is_lhs: bool    # True if assignment target

class ASTLocator:
    """Maps cursor positions to AST nodes and variable names.

    Key features:
    - Column-aware variable detection
    - LHS preference for ambiguous positions (x = x + 1)
    - Function scope detection
    """

    def __init__(self, source: str, filename: str = "<string>"):
        self._source = source
        self._filename = filename
        self._tree: Optional[ast.AST] = None
        self._variables: List[VariableLocation] = []
        self._functions: List[Tuple[str, int, int]] = []  # (name, start_line, end_line)
        self._parse()

    def _parse(self) -> None:
        """Parse source and extract variable locations."""
        try:
            self._tree = ast.parse(self._source, filename=self._filename)
        except SyntaxError:
            self._tree = None
            return

        self._extract_variables()
        self._extract_functions()

    def _extract_variables(self) -> None:
        """Extract all Name nodes with their locations."""
        if self._tree is None:
            return

        # Find all assignment targets first
        lhs_positions: Set[Tuple[int, int]] = set()
        for node in ast.walk(self._tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    self._collect_lhs_positions(target, lhs_positions)
            elif isinstance(node, ast.AnnAssign) and node.target:
                self._collect_lhs_positions(node.target, lhs_positions)
            elif isinstance(node, ast.AugAssign):
                self._collect_lhs_positions(node.target, lhs_positions)
            elif isinstance(node, (ast.For, ast.comprehension)):
                self._collect_lhs_positions(node.target, lhs_positions)

        # Now collect all Name nodes
        for node in ast.walk(self._tree):
            if isinstance(node, ast.Name):
                is_lhs = (node.lineno, node.col_offset) in lhs_positions
                self._variables.append(VariableLocation(
                    name=node.id,
                    line=node.lineno,
                    col_start=node.col_offset,
                    col_end=node.end_col_offset or (node.col_offset + len(node.id)),
                    is_lhs=is_lhs,
                ))

    def _collect_lhs_positions(self, node: ast.AST, positions: Set[Tuple[int, int]]) -> None:
        """Recursively collect positions of assignment targets."""
        if isinstance(node, ast.Name):
            positions.add((node.lineno, node.col_offset))
        elif isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                self._collect_lhs_positions(elt, positions)

    def _extract_functions(self) -> None:
        """Extract function definitions with their line ranges."""
        if self._tree is None:
            return

        for node in ast.walk(self._tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end_line = node.end_lineno or node.lineno
                self._functions.append((node.name, node.lineno, end_line))

    def get_var_at_cursor(self, line: int, col: int) -> Optional[str]:
        """Return variable name at cursor position, or None.

        If multiple variables overlap (rare), prefer LHS.
        """
        candidates = []
        for var in self._variables:
            if var.line == line and var.col_start <= col < var.col_end:
                candidates.append(var)

        if not candidates:
            return None

        # Prefer LHS if ambiguous
        lhs_candidates = [v for v in candidates if v.is_lhs]
        if lhs_candidates:
            return lhs_candidates[0].name

        return candidates[0].name

    def get_var_location_at_cursor(self, line: int, col: int) -> Optional[VariableLocation]:
        """Return full VariableLocation at cursor, or None."""
        for var in self._variables:
            if var.line == line and var.col_start <= col < var.col_end:
                return var
        return None

    def get_all_variables_on_line(self, line: int) -> List[VariableLocation]:
        """Return all variables on a given line."""
        return [v for v in self._variables if v.line == line]

    def get_enclosing_function(self, line: int) -> Optional[str]:
        """Return name of function containing this line, or None."""
        for name, start, end in self._functions:
            if start <= line <= end:
                return name
        return None

    def get_nearest_variable(self, line: int, col: int) -> Optional[VariableLocation]:
        """Find nearest variable to cursor position.

        First checks exact match, then looks on same line within 3 chars.
        """
        # Exact match
        exact = self.get_var_location_at_cursor(line, col)
        if exact:
            return exact

        # Same line, within proximity
        line_vars = self.get_all_variables_on_line(line)
        if not line_vars:
            return None

        # Find closest by column distance
        def distance(v: VariableLocation) -> int:
            if v.col_start <= col < v.col_end:
                return 0
            return min(abs(col - v.col_start), abs(col - v.col_end))

        closest = min(line_vars, key=distance)
        if distance(closest) <= 3:  # Snap within 3 chars
            return closest

        return None

    @property
    def is_valid(self) -> bool:
        """Return True if source was parsed successfully."""
        return self._tree is not None
```

### `pyprobe/analysis/tests/__init__.py`
```python
"""Tests for analysis module."""
```

### `pyprobe/analysis/tests/test_ast_locator.py`
```python
"""Tests for AST locator."""
import pytest
from pyprobe.analysis.ast_locator import ASTLocator

def test_simple_variable():
    source = "x = 42"
    loc = ASTLocator(source)
    assert loc.get_var_at_cursor(1, 0) == "x"
    assert loc.get_var_at_cursor(1, 4) is None  # on "42"

def test_lhs_preference():
    source = "x = x + 1"
    loc = ASTLocator(source)
    # Both x's are on line 1, col 0 is LHS, col 4 is RHS
    var_at_0 = loc.get_var_location_at_cursor(1, 0)
    var_at_4 = loc.get_var_location_at_cursor(1, 4)
    assert var_at_0.is_lhs == True
    assert var_at_4.is_lhs == False

def test_multiple_vars_on_line():
    source = "z = y * h"
    loc = ASTLocator(source)
    vars_on_1 = loc.get_all_variables_on_line(1)
    names = {v.name for v in vars_on_1}
    assert names == {"z", "y", "h"}

def test_function_scope():
    source = '''
def foo():
    x = 1
    return x

def bar():
    y = 2
'''
    loc = ASTLocator(source)
    assert loc.get_enclosing_function(3) == "foo"
    assert loc.get_enclosing_function(7) == "bar"
    assert loc.get_enclosing_function(1) is None

def test_syntax_error():
    source = "x = ("  # Invalid
    loc = ASTLocator(source)
    assert not loc.is_valid
    assert loc.get_var_at_cursor(1, 0) is None
```

---

## Verification

```bash
cd /Users/ppal/repos/pyprobe
python -m pytest pyprobe/analysis/tests/test_ast_locator.py -v
```

---

## Merge Conflict Risk

**None** - All new files.
