import numpy as np
from typing import Dict, List, Any, Optional
from .equation_engine import EquationEngine

class Equation:
    def __init__(self, eq_id: str, expression: str = ""):
        self.id = eq_id
        self.expression = expression
        self.result: Optional[np.ndarray] = None
        self.error: Optional[str] = None

class EquationManager:
    """
    Manages a collection of equations and their evaluation.
    """
    def __init__(self):
        self.engine = EquationEngine()
        self.equations: Dict[str, Equation] = {}
        self._next_eq_idx = 0

    def add_equation(self, expression: str = "") -> Equation:
        eq_id = f"eq{self._next_eq_idx}"
        self._next_eq_idx += 1
        eq = Equation(eq_id, expression)
        self.equations[eq_id] = eq
        return eq

    def remove_equation(self, eq_id: str):
        if eq_id in self.equations:
            del self.equations[eq_id]

    def update_expression(self, eq_id: str, expression: str):
        if eq_id in self.equations:
            self.equations[eq_id].expression = expression
            self.equations[eq_id].result = None
            self.equations[eq_id].error = None

    def evaluate_all(self, trace_data: Dict[str, Any]):
        """
        Evaluates all equations, handling dependencies.
        """
        # Create a combined data dict with traces
        data = trace_data.copy()
        
        # Simple iterative evaluation to handle dependencies
        # In a real app, we might want a DAG, but for now we'll just 
        # iterate a few times or sort them.
        # Since eq<n> only depends on lower or higher eq<m>, 
        # we can just try to evaluate multiple times until stable or max iterations.
        
        to_evaluate = list(self.equations.values())
        max_iters = len(to_evaluate) + 1
        
        for _ in range(max_iters):
            changed = False
            for eq in to_evaluate:
                if not eq.expression.strip():
                    continue
                    
                try:
                    # Try to evaluate
                    new_result = self.engine.evaluate(eq.expression, data)
                    
                    # Check if result changed (approximately)
                    if eq.result is None or not np.array_equal(new_result, eq.result):
                        eq.result = new_result
                        eq.error = None
                        data[eq.id] = eq.result
                        changed = True
                except Exception as e:
                    # If it fails, it might be due to a missing dependency that will be 
                    # available in a later iteration.
                    eq.error = str(e)
                    eq.result = None
            
            if not changed:
                break
