# Filter Non-Probeable Symbols

## Problem
Users can probe symbols that shouldn't be probed:
- Module names (`np`, `time`)
- Function names (`print`, `main`, `generate_qam_signal`)
- Class names
- Built-in names

This clutters the probe panel with meaningless probes and confuses users.

## User Review Required

> [!IMPORTANT]
> **Design Decision**: Should we allow probing function calls like `np.sin(...)` for their return value?
> Initial implementation will ONLY allow probing of **data variables** (LHS assignments).

## Proposed Changes

### Analysis Component

#### [MODIFY] [ast_locator.py](file:///Users/ppal/repos/pyprobe/pyprobe/analysis/ast_locator.py)

Add classification to `VariableLocation`:

```python
class SymbolType(Enum):
    DATA_VARIABLE = "data"      # LHS of assignment → PROBEABLE
    FUNCTION_CALL = "call"      # Function being called → NOT probeable
    MODULE_REF = "module"       # Module access (np.xyz) → NOT probeable
    FUNCTION_DEF = "func_def"   # Function name in def → NOT probeable
    UNKNOWN = "unknown"         # Default → NOT probeable
```

Add to `VariableLocation`:
```python
symbol_type: SymbolType = SymbolType.UNKNOWN
```

**Changes to `_extract_variables()`:**
1. Track LHS positions (already done) → mark as `DATA_VARIABLE`
2. Track function call targets → mark as `FUNCTION_CALL`
3. Track attribute access bases (`np.` in `np.sin`) → mark as `MODULE_REF`
4. Track function definition names → mark as `FUNCTION_DEF`

Add new method:
```python
def is_probeable(self, var_loc: VariableLocation) -> bool:
    """Return True if this variable can be probed."""
    return var_loc.symbol_type == SymbolType.DATA_VARIABLE
```

---

### GUI Component

#### [MODIFY] [code_viewer.py](file:///Users/ppal/repos/pyprobe/pyprobe/gui/code_viewer.py)

In `_get_anchor_at_position()`:
```python
# After finding var_loc
if var_loc is None or not self._ast_locator.is_probeable(var_loc):
    logger.debug(f"_get_anchor_at_position: symbol not probeable: {var_loc}")
    return None
```

In `_draw_hover_highlight()`:
```python
# Only draw hover if probeable
if not self._ast_locator.is_probeable(var_loc):
    return  # No visual feedback for non-probeable
```

---

## Verification Plan

### Automated Tests

Add to `pyprobe/analysis/tests/test_ast_locator.py`:

```python
def test_symbol_classification():
    source = '''
import numpy as np

def foo(x):
    result = np.sin(x) + x
    return result
'''
    loc = ASTLocator(source)
    
    # Line 5: result = np.sin(x) + x
    vars_on_5 = loc.get_all_variables_on_line(5)
    
    # Check probeable
    result_var = next(v for v in vars_on_5 if v.name == "result")
    x_vars = [v for v in vars_on_5 if v.name == "x"]
    np_var = next(v for v in vars_on_5 if v.name == "np")
    
    assert loc.is_probeable(result_var) == True   # LHS assignment
    assert loc.is_probeable(np_var) == False      # Module reference
    
    # x on RHS is arguable - initially NOT probeable (only LHS)
    for x_var in x_vars:
        if not x_var.is_lhs:
            assert loc.is_probeable(x_var) == False
```

Run:
```bash
cd /Users/ppal/repos/pyprobe && python -m pytest pyprobe/analysis/tests/test_ast_locator.py -v
```

### Manual Verification

**Steps to test:**
1. Run: `python -m pyprobe --loglevel DEBUG examples/dsp_demo.py`
2. Hover over `np` on line 78 → **Should NOT** show hover highlight
3. Hover over `print` on line 54 → **Should NOT** show hover highlight  
4. Hover over `received_symbols` on line 72 → **Should** show hover highlight
5. Click on `np` → **Should NOT** create probe panel
6. Click on `received_symbols` → **Should** create probe panel

**Log verification (check `/tmp/pyprobe_debug.log`):**
- When clicking `np`: Should see `_get_anchor_at_position: symbol not probeable`
- When clicking `received_symbols`: Should NOT see that message

---

## Logging Strategy

Add to `ast_locator.py`:
```python
from pyprobe.logging import get_logger
logger = get_logger(__name__)
```

In `_extract_variables()`:
```python
logger.debug(f"Classified {node.id} at L{node.lineno}:C{node.col_offset} as {symbol_type}")
```

In `is_probeable()`:
```python
logger.debug(f"is_probeable({var_loc.name}): type={var_loc.symbol_type}, result={result}")
```

This allows verification via log analysis without running the full GUI.
