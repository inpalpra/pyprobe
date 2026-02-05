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
