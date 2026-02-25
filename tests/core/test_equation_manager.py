import pytest
import numpy as np
from pyprobe.core.equation_manager import EquationManager

def test_recursive_equations() -> None:
    manager = EquationManager()
    tr_data = {"tr0": np.array([1, 2, 3])}
    
    eq0 = manager.add_equation("tr0 * 2") # [2, 4, 6]
    eq1 = manager.add_equation("eq0 + 1") # [3, 5, 7]
    
    manager.evaluate_all(tr_data)
    
    assert np.array_equal(eq0.result, np.array([2, 4, 6]))
    assert np.array_equal(eq1.result, np.array([3, 5, 7]))

def test_circular_dependency_graceful_failure() -> None:
    manager = EquationManager()
    eq0 = manager.add_equation("eq1 + 1")
    eq1 = manager.add_equation("eq0 + 1")
    
    # Should not crash, but result might be None or Error
    manager.evaluate_all({})
    
    # At least one will have an error
    assert eq0.error or eq1.error
