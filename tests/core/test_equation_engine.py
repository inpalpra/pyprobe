import pytest
import numpy as np
from pyprobe.core.equation_engine import EquationEngine

def test_basic_arithmetic() -> None:
    engine = EquationEngine()
    data = {"tr0": np.array([1, 2, 3])}
    
    result = engine.evaluate("tr0 * 2", data)
    assert np.array_equal(result, np.array([2, 4, 6]))

def test_complex_arithmetic() -> None:
    engine = EquationEngine()
    data = {
        "tr0": np.array([1+1j, 2+2j]),
        "tr1": np.array([1-1j, 2-2j])
    }
    
    result = engine.evaluate("tr0 + tr1", data)
    assert np.array_equal(result, np.array([2+0j, 4+0j]))

def test_numpy_functions() -> None:
    engine = EquationEngine()
    data = {"tr0": np.array([0, np.pi/2, np.pi])}
    
    result = engine.evaluate("np.sin(tr0)", data)
    assert np.allclose(result, np.array([0, 1, 0]), atol=1e-7)

def test_scipy_signal_functions() -> None:
    engine = EquationEngine()
    data = {"tr0": np.random.randn(100)}
    # Use something from signal if we decide to include it
    # For now let's just test np.abs
    result = engine.evaluate("np.abs(tr0)", data)
    assert np.all(result >= 0)

def test_syntax_error() -> None:
    engine = EquationEngine()
    data = {"tr0": np.array([1])}
    
    with pytest.raises(ValueError, match="Invalid expression"):
        engine.evaluate("tr0 + * 2", data)

def test_missing_variable() -> None:
    engine = EquationEngine()
    data = {"tr0": np.array([1])}
    
    with pytest.raises(ValueError, match="Name 'tr1' is not defined"):
        engine.evaluate("tr1 * 2", data)

def test_recursive_evaluation() -> None:
    # This will be handled by the caller managing multiple equations
    # But EquationEngine should support passing previous equation results in data
    engine = EquationEngine()
    data = {
        "tr0": np.array([1, 2]),
        "eq0": np.array([10, 20])
    }
    result = engine.evaluate("tr0 + eq0", data)
    assert np.array_equal(result, np.array([11, 22]))

def test_safety_restriction() -> None:
    engine = EquationEngine()
    data = {}
    # Try to access something forbidden
    with pytest.raises(ValueError, match="Forbidden name"):
        engine.evaluate("__import__('os').system('ls')", data)
