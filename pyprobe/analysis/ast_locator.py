"""AST-based source code analysis for variable location."""
import ast
from enum import Enum
from typing import Optional, List, Tuple, Set
from dataclasses import dataclass, field

from pyprobe.logging import get_logger

logger = get_logger(__name__)


class SymbolType(Enum):
    """Classification of symbol types for probeability determination."""
    DATA_VARIABLE = "data"      # LHS of assignment → PROBEABLE
    FUNCTION_CALL = "call"      # Function being called → NOT probeable
    MODULE_REF = "module"       # Module access (np.xyz) → NOT probeable
    FUNCTION_DEF = "func_def"   # Function name in def → NOT probeable
    UNKNOWN = "unknown"         # Default → NOT probeable


@dataclass
class VariableLocation:
    """Location of a variable in source code."""
    name: str
    line: int       # 1-indexed
    col_start: int  # 0-indexed
    col_end: int    # 0-indexed, exclusive
    is_lhs: bool    # True if assignment target
    symbol_type: SymbolType = field(default=SymbolType.UNKNOWN)


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
        """Extract all Name nodes with their locations and symbol types."""
        if self._tree is None:
            return

        # Collect positions for each symbol type
        lhs_positions: Set[Tuple[int, int]] = set()
        call_positions: Set[Tuple[int, int]] = set()  # Function calls
        module_positions: Set[Tuple[int, int]] = set()  # Attribute base (e.g., np in np.sin)
        func_def_positions: Set[Tuple[int, int]] = set()  # Function/class def names

        self._collect_lhs_positions_from_tree(self._tree, lhs_positions)
        self._collect_special_positions(self._tree, call_positions, module_positions, func_def_positions)

        # Now collect all Name nodes and classify them
        for node in ast.walk(self._tree):
            if isinstance(node, ast.Name):
                pos = (node.lineno, node.col_offset)
                
                # Determine symbol type (priority order matters)
                if pos in lhs_positions:
                    symbol_type = SymbolType.DATA_VARIABLE
                elif pos in func_def_positions:
                    symbol_type = SymbolType.FUNCTION_DEF
                elif pos in call_positions:
                    symbol_type = SymbolType.FUNCTION_CALL
                elif pos in module_positions:
                    symbol_type = SymbolType.MODULE_REF
                else:
                    symbol_type = SymbolType.UNKNOWN
                
                is_lhs = pos in lhs_positions
                var_loc = VariableLocation(
                    name=node.id,
                    line=node.lineno,
                    col_start=node.col_offset,
                    col_end=node.end_col_offset or (node.col_offset + len(node.id)),
                    is_lhs=is_lhs,
                    symbol_type=symbol_type,
                )
                self._variables.append(var_loc)
                logger.debug(f"Classified {node.id} at L{node.lineno}:C{node.col_offset} as {symbol_type}")

    def _collect_special_positions(
        self, 
        tree: ast.AST, 
        call_positions: Set[Tuple[int, int]],
        module_positions: Set[Tuple[int, int]],
        func_def_positions: Set[Tuple[int, int]]
    ) -> None:
        """Collect positions of function calls, module refs, and function defs."""
        for node in ast.walk(tree):
            # Function definitions - the function name itself
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Note: node.name is just a string, but we need to find corresponding Name nodes
                # Function defs don't have Name nodes for their own name, so we track line/col
                # Actually FunctionDef.name is a str, not a Name node, so this won't be in _variables
                pass
            
            # Class definitions - similar, class name is a string attribute
            if isinstance(node, ast.ClassDef):
                pass
            
            # Function calls
            if isinstance(node, ast.Call):
                func = node.func
                # Direct call: foo()
                if isinstance(func, ast.Name):
                    call_positions.add((func.lineno, func.col_offset))
                # Method call: obj.method() - mark 'obj' as module ref
                elif isinstance(func, ast.Attribute):
                    self._collect_attribute_base_positions(func, module_positions)
            
            # Attribute access (not a call, just np.something)
            if isinstance(node, ast.Attribute):
                # If this attribute is the value of another attribute (nested: np.sin.something)
                # or if it's part of a call (np.sin()), we handle module refs
                self._collect_attribute_base_positions(node, module_positions)

    def _collect_attribute_base_positions(
        self, 
        node: ast.Attribute, 
        positions: Set[Tuple[int, int]]
    ) -> None:
        """Recursively collect base Name positions from attribute chains."""
        val = node.value
        if isinstance(val, ast.Name):
            # This is the base of the attribute chain (e.g., 'np' in np.sin)
            positions.add((val.lineno, val.col_offset))
        elif isinstance(val, ast.Attribute):
            # Nested attribute, recurse
            self._collect_attribute_base_positions(val, positions)

    def _collect_lhs_positions_from_tree(self, tree: ast.AST, positions: Set[Tuple[int, int]]) -> None:
        """Walk tree and collect all assignment target positions."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    self._collect_lhs_positions(target, positions)
            elif isinstance(node, ast.AnnAssign) and node.target:
                self._collect_lhs_positions(node.target, positions)
            elif isinstance(node, ast.AugAssign):
                self._collect_lhs_positions(node.target, positions)
            elif isinstance(node, (ast.For, ast.comprehension)):
                self._collect_lhs_positions(node.target, positions)

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

    def is_probeable(self, var_loc: VariableLocation) -> bool:
        """Return True if this variable can be probed.
        
        Only DATA_VARIABLE symbols (LHS of assignments) are probeable.
        Function calls, module references, and unknown symbols are not.
        """
        result = var_loc.symbol_type == SymbolType.DATA_VARIABLE
        logger.debug(f"is_probeable({var_loc.name}): type={var_loc.symbol_type}, result={result}")
        return result

    @property
    def is_valid(self) -> bool:
        """Return True if source was parsed successfully."""
        return self._tree is not None
