# Filter Non-Probeable Symbols (Revised)

## Problem
~~Users can probe symbols that shouldn't be probed~~ → **Revised approach**: Allow probing all symbols, but handle gracefully when no data is available.

Original issue: Probing `np`, `print`, etc. created empty/confusing probe panels.

## User Feedback (2026-02-06)

> [!IMPORTANT]
> **Design Decision Resolved**: Allow probing everything. Show "Nothing to show" for non-data symbols.
> 
> Future enhancements:
> - Scalar value history graphs
> - Custom probes per symbol type (function return values, module info, etc.)

## Current State

Symbol classification is already implemented:
- `SymbolType` enum in `ast_locator.py` ✅
- `is_probeable()` method ✅
- **Problem**: `code_viewer.py` blocks probing non-DATA_VARIABLE symbols

## Proposed Changes

### Phase 1: Revert Strict Filtering (This Fix)

#### [MODIFY] [code_viewer.py](file:///Users/ppal/repos/pyprobe/pyprobe/gui/code_viewer.py)

**Remove probeability check in `_get_anchor_at_position()`:**
```diff
        var_loc = self._ast_locator.get_nearest_variable(line, col)
        if var_loc is None:
            return None
-        
-        # Check if symbol is probeable
-        if not self._ast_locator.is_probeable(var_loc):
-            logger.debug(f"_get_anchor_at_position: symbol not probeable: {var_loc}")
-            return None
```

**Remove probeability check in `_draw_hover_highlight()`:**
```diff
-        # Only draw hover if probeable
-        if self._ast_locator is not None and not self._ast_locator.is_probeable(var_loc):
-            return  # No visual feedback for non-probeable
```

---

#### [MODIFY] [probe_panel.py](file:///Users/ppal/repos/pyprobe/pyprobe/gui/probe_panel.py)

**Add "Nothing to show" placeholder when no data arrives:**
- In `ProbePanel` widget, show placeholder text initially
- Replace placeholder with actual graph when data arrives
- If panel exists for N seconds with no data, keep showing placeholder

---

### Phase 2: Future Enhancements (Not This PR)

- Scalar history graphs (plot value over multiple runs)
- Function call probes (display return value)
- Module probes (display module info)

---

## Verification Plan

### Manual Verification

**Run:**
```bash
python -m pyprobe --loglevel DEBUG examples/dsp_demo.py
```

**Test:**
1. Click `np` (line 13) → **Should** create probe panel with "Nothing to show"
2. Click `print` (line 54) → **Should** create probe panel with "Nothing to show"
3. Click `received_symbols` (line 72) → **Should** create probe panel, shows graph when RUN
4. Click `x` (argument in function) → **Should** create probe panel (may or may not show data depending on tracer)

---

## Logging Strategy

Keep existing classification logging in `ast_locator.py` for debugging symbol types.
Add to `probe_panel.py`:
```python
logger.debug(f"ProbePanel: no data received for {anchor}, showing placeholder")
```

