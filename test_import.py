#!/usr/bin/env python
"""Test script to verify imports work."""
import sys
sys.path.insert(0, '/Users/ppal/repos/pyprobe')

from pyprobe.analysis.ast_locator import ASTLocator

# Test basic functionality
source = "x = 42"
loc = ASTLocator(source)
result = loc.get_var_at_cursor(1, 0)
print(f"Test 1: {result == 'x'}")

# Test LHS preference
source2 = "x = x + 1"
loc2 = ASTLocator(source2)
var_at_0 = loc2.get_var_location_at_cursor(1, 0)
var_at_4 = loc2.get_var_location_at_cursor(1, 4)
print(f"Test 2: LHS is_lhs={var_at_0.is_lhs}, RHS is_lhs={var_at_4.is_lhs}")

print("All imports successful!")
