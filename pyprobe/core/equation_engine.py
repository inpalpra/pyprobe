import numpy as np
import scipy.signal as signal
from typing import Dict, Any

class EquationEngine:
    """
    Evaluates mathematical expressions on trace data.
    """
    def __init__(self):
        # Restricted global scope for eval
        self.safe_globals = {
            "np": np,
            "numpy": np,
            "signal": signal,
            "abs": abs,
            "min": min,
            "max": max,
            "sum": sum,
            "len": len,
        }
        # Add all numpy functions to the top level for convenience
        for name in dir(np):
            if not name.startswith("_"):
                obj = getattr(np, name)
                if callable(obj):
                    self.safe_globals[name] = obj

    def evaluate(self, expression: str, data: Dict[str, Any]) -> Any:
        """
        Evaluates the expression using the provided data dictionary.
        
        Args:
            expression: The string expression to evaluate
            data: Mapping of variable names (tr0, eq0, etc.) to values
            
        Returns:
            The result of the evaluation (usually a numpy array)
            
        Raises:
            ValueError: If the expression is invalid or contains forbidden operations
        """
        if not expression or not expression.strip():
            raise ValueError("Empty expression")

        # Basic safety check for double underscores (prevents __import__, etc.)
        if "__" in expression:
            raise ValueError("Forbidden name: expression contains '__'")

        try:
            # Evaluate with restricted globals and variable data as locals
            result = eval(expression, {"__builtins__": {}}, {**self.safe_globals, **data})
            return result
        except NameError as e:
            raise ValueError(f"Name {str(e).split(' ')[1]} is not defined")
        except SyntaxError as e:
            raise ValueError(f"Invalid expression syntax: {e.msg}")
        except Exception as e:
            raise ValueError(f"Evaluation error: {str(e)}")
