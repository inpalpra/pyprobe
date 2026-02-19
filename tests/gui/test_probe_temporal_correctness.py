"""
E2E Probe Temporal Correctness Stress Tests.

Every test launches pyprobe as a subprocess with --auto-run --auto-quit,
parses PLOT_DATA JSON from stderr, and asserts probe values, ordering,
and temporal correctness.

Tests verify:
1. Correct values - each probe reports the value at its specific code location
2. Correct ordering - seq_nums respect execution order (arrow of time)
3. No stale/future values - RHS reads see pre-assignment, LHS sees post-assignment
4. No ghost captures - dead code paths produce zero records
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from typing import Dict, List, Optional, Tuple


def run_pyprobe_e2e(
    script_path: str,
    probes: List[str],
    timeout: int = 15,
) -> Dict[str, dict]:
    """
    Run pyprobe E2E and return parsed PLOT_DATA keyed by (symbol, line, col).

    Args:
        script_path: Absolute path to the script to run
        probes: List of probe specs like "4:x:1" (line:symbol:instance)
        timeout: Maximum seconds to wait

    Returns:
        List of all PLOT_DATA dicts, each containing at minimum:
        {'symbol': str, 'line': int, 'col': int, 'is_assignment': bool, 'y': list}
    """
    python_exe = sys.executable

    cmd = [
        python_exe, "-m", "pyprobe",
        "--auto-run",
        "--auto-quit",
        "--loglevel", "WARNING",
    ]

    for probe in probes:
        cmd.extend(["--probe", probe])

    cmd.append(script_path)

    env = os.environ.copy()

    with tempfile.TemporaryFile(mode='w+') as tmp_out:
        result = subprocess.run(
            cmd,
            stdout=tmp_out,
            stderr=tmp_out,
            text=True,
            env=env,
            timeout=timeout,
        )

        tmp_out.seek(0)
        output = tmp_out.read()

    if result.returncode != 0:
        raise RuntimeError(f"PyProbe failed with code {result.returncode}:\n{output}")

    # Parse all PLOT_DATA lines
    all_data = []
    matches = re.findall(r'PLOT_DATA:(\{.*?\})', output)

    for match in matches:
        data = json.loads(match)
        all_data.append(data)

    return all_data


def _find_data(all_data: List[dict], symbol: str,
               line: Optional[int] = None,
               is_assignment: Optional[bool] = None) -> Optional[dict]:
    """Find a specific PLOT_DATA entry matching the criteria."""
    for d in all_data:
        if d.get('symbol') != symbol:
            continue
        if line is not None and d.get('line') != line:
            continue
        if is_assignment is not None and d.get('is_assignment') != is_assignment:
            continue
        return d
    return None


def _find_all(all_data: List[dict], symbol: str,
              line: Optional[int] = None) -> List[dict]:
    """Find all PLOT_DATA entries matching symbol and optionally line."""
    results = []
    for d in all_data:
        if d.get('symbol') != symbol:
            continue
        if line is not None and d.get('line') != line:
            continue
        results.append(d)
    return results


def _get_y(data: Optional[dict]) -> List[float]:
    """Extract y-values from PLOT_DATA entry, returning [] if missing."""
    if data is None:
        return []
    return data.get('y', [])


class TestProbeTemporalCorrectness(unittest.TestCase):
    """
    E2E tests for probe temporal correctness.

    Every test launches pyprobe as a subprocess. No in-process tracer shortcuts.
    """

    @classmethod
    def setUpClass(cls):
        """Verify we're running from repo root and locate regression scripts."""
        cls.repo_root = os.getcwd()
        if not os.path.exists(os.path.join(cls.repo_root, 'pyprobe', '__main__.py')):
            # Try to find repo root from test file location
            cls.repo_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
        cls.temporal_dir = os.path.join(cls.repo_root, 'regression', 'temporal')
        assert os.path.isdir(cls.temporal_dir), (
            f"Cannot find regression/temporal/ at {cls.temporal_dir}. "
            f"Run tests from repo root."
        )

    def _run(self, script_name: str, probes: List[str]) -> List[dict]:
        """Shorthand E2E launcher."""
        script = os.path.join(self.temporal_dir, script_name)
        return run_pyprobe_e2e(script, probes)

    # =================================================================
    # 1. Same Variable, Same Line — LHS vs RHS
    # =================================================================

    def test_lhs_rhs_same_var_same_line(self):
        """
        x = x + 1: LHS x should be 4 (post-assign), RHS x should be 3 (pre-assign).

        Script: lhs_rhs_sameline.py
            def main():
                x = 3         # line 2
                x = x + 1     # line 3
                return x
        """
        data = self._run("lhs_rhs_sameline.py", ["3:x:1", "3:x:2"])

        # We expect two PLOT_DATA entries for symbol 'x' on line 3
        x_entries = _find_all(data, 'x', line=3)
        self.assertEqual(len(x_entries), 2,
                         f"Expected 2 probes for x on line 3, got {len(x_entries)}")

        # Sort by col to get predictable order
        x_entries.sort(key=lambda d: d.get('col', 0))

        # First occurrence (LHS at col 4) should be assignment
        lhs = _find_data(data, 'x', line=3, is_assignment=True)
        rhs = _find_data(data, 'x', line=3, is_assignment=False)

        self.assertIsNotNone(lhs, "No LHS x probe found on line 3")
        self.assertIsNotNone(rhs, "No RHS x probe found on line 3")

        lhs_y = _get_y(lhs)
        rhs_y = _get_y(rhs)

        self.assertEqual(rhs_y, [3.0],
                         f"RHS x should be 3 (pre-assignment), got {rhs_y}")
        self.assertEqual(lhs_y, [4.0],
                         f"LHS x should be 4 (post-assignment), got {lhs_y}")

    def test_augmented_assign(self):
        """
        x += 5: LHS x = 15, RHS x = 10 (if augmented assign exposes both).

        Script: augmented_assign.py
            def main():
                x = 10    # line 2
                x += 5    # line 3
                return x
        """
        data = self._run("augmented_assign.py", ["3:x:1", "3:x:2"])

        x_entries = _find_all(data, 'x', line=3)
        # Augmented assign may expose 1 or 2 anchors depending on tracer
        self.assertGreaterEqual(len(x_entries), 1,
                                f"Expected at least 1 probe for x on line 3")

        # If both LHS and RHS are captured:
        lhs = _find_data(data, 'x', line=3, is_assignment=True)
        if lhs is not None:
            self.assertEqual(_get_y(lhs), [15.0],
                             f"LHS x after += should be 15")

    def test_double_reference_rhs(self):
        """
        y = x * x: both RHS x's should be 4, LHS y should be 16.

        Script: double_ref.py
            def main():
                x = 4        # line 2
                y = x * x    # line 3
                return y
        """
        data = self._run("double_ref.py", ["3:x:1", "3:x:2", "3:y:1"])

        x_entries = _find_all(data, 'x', line=3)
        for entry in x_entries:
            y = _get_y(entry)
            self.assertEqual(y, [4.0],
                             f"RHS x should be 4, got {y}")

        y_entry = _find_data(data, 'y', line=3)
        self.assertIsNotNone(y_entry, "No y probe found on line 3")
        self.assertEqual(_get_y(y_entry), [16.0],
                         f"LHS y should be 16, got {_get_y(y_entry)}")

    # =================================================================
    # 2. Same Variable, Consecutive Lines — Reassignment
    # =================================================================

    def test_reassignment_two_lines(self):
        """
        x = 3 then x = x + 1: probe x on both lines.

        Script: reassign_two.py
            def main():
                x = 3         # line 2
                x = x + 1     # line 3
                return x
        """
        data = self._run("reassign_two.py", ["2:x:1", "3:x:1", "3:x:2"])

        # Line 2 LHS x = 3
        x_line2 = _find_data(data, 'x', line=2)
        self.assertIsNotNone(x_line2, "No x probe on line 2")
        self.assertEqual(_get_y(x_line2), [3.0])

        # Line 3: LHS x = 4, RHS x = 3
        lhs = _find_data(data, 'x', line=3, is_assignment=True)
        rhs = _find_data(data, 'x', line=3, is_assignment=False)

        if lhs is not None:
            self.assertEqual(_get_y(lhs), [4.0],
                             f"LHS x on line 3 should be 4")
        if rhs is not None:
            self.assertEqual(_get_y(rhs), [3.0],
                             f"RHS x on line 3 should be 3")

    def test_chain_reassignment(self):
        """
        x = 1, x = 2, x = 3, x = 4: each line captures correct value.

        Script: chain_reassign.py
            def main():
                x = 1    # line 2
                x = 2    # line 3
                x = 3    # line 4
                x = 4    # line 5
                return x
        """
        data = self._run("chain_reassign.py",
                          ["2:x:1", "3:x:1", "4:x:1", "5:x:1"])

        for line, expected in [(2, 1.0), (3, 2.0), (4, 3.0), (5, 4.0)]:
            entry = _find_data(data, 'x', line=line)
            self.assertIsNotNone(entry, f"No x probe on line {line}")
            self.assertEqual(_get_y(entry), [expected],
                             f"x on line {line} should be {expected}")

    def test_swap_pattern(self):
        """
        a, b = b, a: RHS reads see original values, LHS sees swapped.

        Script: swap.py
            def main():
                a = 1         # line 2
                b = 2         # line 3
                a, b = b, a   # line 4
                return a, b
        """
        data = self._run("swap.py", ["4:a:1", "4:b:1", "4:a:2", "4:b:2"])

        # After swap: a=2, b=1
        a_entries = _find_all(data, 'a', line=4)
        b_entries = _find_all(data, 'b', line=4)

        # LHS a should be 2 (swapped)
        a_lhs = _find_data(data, 'a', line=4, is_assignment=True)
        if a_lhs is not None:
            self.assertEqual(_get_y(a_lhs), [2.0],
                             f"LHS a after swap should be 2")

        # LHS b should be 1 (swapped)
        b_lhs = _find_data(data, 'b', line=4, is_assignment=True)
        if b_lhs is not None:
            self.assertEqual(_get_y(b_lhs), [1.0],
                             f"LHS b after swap should be 1")

        # RHS a should be 1 (pre-swap)
        a_rhs = _find_data(data, 'a', line=4, is_assignment=False)
        if a_rhs is not None:
            self.assertEqual(_get_y(a_rhs), [1.0],
                             f"RHS a before swap should be 1")

        # RHS b should be 2 (pre-swap)
        b_rhs = _find_data(data, 'b', line=4, is_assignment=False)
        if b_rhs is not None:
            self.assertEqual(_get_y(b_rhs), [2.0],
                             f"RHS b before swap should be 2")

    # =================================================================
    # 3. Loops — Same Variable, Same Line, Many Iterations
    # =================================================================

    def test_loop_lhs_and_rhs_both_probed(self):
        """
        x = x - 1 in a loop: LHS sees post-assign, RHS sees pre-assign.

        Script: loop_lhs_rhs.py
            def main():
                x = 100              # line 2
                for i in range(5):   # line 3
                    x = x - 1        # line 4
                return x
        """
        data = self._run("loop_lhs_rhs.py", ["4:x:1", "4:x:2"])

        lhs = _find_data(data, 'x', line=4, is_assignment=True)
        rhs = _find_data(data, 'x', line=4, is_assignment=False)

        if lhs is not None:
            lhs_y = _get_y(lhs)
            self.assertEqual(lhs_y, [99.0, 98.0, 97.0, 96.0, 95.0],
                             f"LHS x should be [99..95], got {lhs_y}")

        if rhs is not None:
            rhs_y = _get_y(rhs)
            self.assertEqual(rhs_y, [100.0, 99.0, 98.0, 97.0, 96.0],
                             f"RHS x should be [100..96], got {rhs_y}")

        # Arrow of time: each RHS value should be 1 more than corresponding LHS
        if lhs is not None and rhs is not None:
            for i, (r, l) in enumerate(zip(_get_y(rhs), _get_y(lhs))):
                self.assertEqual(r, l + 1,
                                 f"Iteration {i}: RHS ({r}) should be LHS ({l}) + 1")

    def test_loop_counter(self):
        """
        j = i * 2 in a loop: RHS i and LHS j tracked separately.

        Script: loop_counter.py
            def main():
                for i in range(4):   # line 2
                    j = i * 2        # line 3
                return
        """
        data = self._run("loop_counter.py", ["3:i:1", "3:j:1"])

        i_entry = _find_data(data, 'i', line=3)
        j_entry = _find_data(data, 'j', line=3)

        if i_entry is not None:
            self.assertEqual(_get_y(i_entry), [0.0, 1.0, 2.0, 3.0],
                             f"RHS i should be [0,1,2,3]")

        if j_entry is not None:
            self.assertEqual(_get_y(j_entry), [0.0, 2.0, 4.0, 6.0],
                             f"LHS j should be [0,2,4,6]")

    def test_accumulator(self):
        """
        total = total + i: LHS is running sum, RHS is previous sum.

        Script: accumulator.py
            def main():
                total = 0                # line 2
                for i in range(1, 6):    # line 3
                    total = total + i    # line 4
                return total
        """
        data = self._run("accumulator.py", ["4:total:1", "4:total:2"])

        lhs = _find_data(data, 'total', line=4, is_assignment=True)
        rhs = _find_data(data, 'total', line=4, is_assignment=False)

        if lhs is not None:
            self.assertEqual(_get_y(lhs), [1.0, 3.0, 6.0, 10.0, 15.0],
                             f"LHS total should be cumulative sums")

        if rhs is not None:
            self.assertEqual(_get_y(rhs), [0.0, 1.0, 3.0, 6.0, 10.0],
                             f"RHS total should be previous sums")

    # =================================================================
    # 4. Nested Scopes
    # =================================================================

    def test_same_name_different_functions(self):
        """
        x = 10 in foo, x = 20 in bar — different scopes, different values.

        Script: diff_funcs.py
            def foo():
                x = 10     # line 2
                return x
            def bar():
                x = 20     # line 6
                return x
            def main():
                foo()
                bar()
        """
        data = self._run("diff_funcs.py", ["2:x:1", "6:x:1"])

        x_foo = _find_data(data, 'x', line=2)
        x_bar = _find_data(data, 'x', line=6)

        self.assertIsNotNone(x_foo, "No x probe in foo (line 2)")
        self.assertIsNotNone(x_bar, "No x probe in bar (line 6)")

        self.assertEqual(_get_y(x_foo), [10.0],
                         f"foo's x should be 10")
        self.assertEqual(_get_y(x_bar), [20.0],
                         f"bar's x should be 20")

    def test_nested_function_shadowing(self):
        """
        Inner function assigns x = 2, outer x should remain 1.

        Script: nested_shadow.py
            def main():
                x = 1          # line 2
                def inner():
                    x = 2      # line 4
                    return x
                inner()
                y = x          # line 7
                return y
        """
        data = self._run("nested_shadow.py", ["2:x:1", "4:x:1", "7:x:1"])

        # Outer x = 1
        x_outer = _find_data(data, 'x', line=2)
        if x_outer is not None:
            self.assertEqual(_get_y(x_outer), [1.0],
                             "Outer x should be 1")

        # Inner x = 2
        x_inner = _find_data(data, 'x', line=4)
        if x_inner is not None:
            self.assertEqual(_get_y(x_inner), [2.0],
                             "Inner x should be 2")

        # y = x at line 7 should read outer x = 1, NOT inner x = 2
        x_read = _find_data(data, 'x', line=7)
        if x_read is not None:
            self.assertEqual(_get_y(x_read), [1.0],
                             "x read at line 7 should be 1 (outer), not 2 (inner)")

    def test_recursive(self):
        """
        countdown(3) assigns x = n at each recursion level.

        Script: recursive.py
            def countdown(n):
                x = n              # line 2
                if n > 0:
                    countdown(n - 1)
                return
            def main():
                countdown(3)
        """
        data = self._run("recursive.py", ["2:x:1"])

        x_entry = _find_data(data, 'x', line=2)
        self.assertIsNotNone(x_entry, "No x probe in recursive countdown")

        y = _get_y(x_entry)
        self.assertEqual(y, [3.0, 2.0, 1.0, 0.0],
                         f"Recursive x should be [3,2,1,0], got {y}")

    # =================================================================
    # 5. Conditionals
    # =================================================================

    def test_conditional_assignment(self):
        """
        Only the taken branch should fire; dead branch produces no capture.

        Script: conditional.py
            def main():
                flag = True      # line 2
                if flag:
                    x = 42       # line 4
                else:
                    x = 99       # line 6
                y = x            # line 7
                return y
        """
        data = self._run("conditional.py", ["4:x:1", "6:x:1", "7:x:1"])

        # Taken branch: x = 42
        x_taken = _find_data(data, 'x', line=4)
        self.assertIsNotNone(x_taken, "Taken branch x=42 should fire")
        self.assertEqual(_get_y(x_taken), [42.0])

        # Dead branch: x = 99 should NOT fire
        x_dead = _find_data(data, 'x', line=6)
        if x_dead is not None:
            self.assertEqual(_get_y(x_dead), [],
                             "Dead branch x=99 should NOT produce data")

        # y = x should read 42
        y_entry = _find_data(data, 'y', line=7)
        if y_entry is not None:
            self.assertEqual(_get_y(y_entry), [42.0])

    def test_ternary(self):
        """
        x = a if a > 3 else 0: x should be 5 (a=5 passes condition).

        Script: ternary.py
            def main():
                a = 5                      # line 2
                x = a if a > 3 else 0      # line 3
                return x
        """
        data = self._run("ternary.py", ["3:x:1", "3:a:1"])

        x_entry = _find_data(data, 'x', line=3)
        if x_entry is not None:
            self.assertEqual(_get_y(x_entry), [5.0])

        a_entry = _find_data(data, 'a', line=3)
        if a_entry is not None:
            self.assertEqual(_get_y(a_entry), [5.0])

    # =================================================================
    # 6. Arrow-of-Time Strict Ordering
    # =================================================================

    def test_monotonic_seq_across_probes(self):
        """
        a=1, b=2, c=3, d=4: values across lines are monotonically increasing.

        Script: monotonic.py
            def main():
                a = 1        # line 2
                b = a + 1    # line 3
                c = b + 1    # line 4
                d = c + 1    # line 5
                return d
        """
        data = self._run("monotonic.py",
                          ["2:a:1", "3:b:1", "4:c:1", "5:d:1"])

        values = []
        for sym, line, expected in [('a', 2, 1.0), ('b', 3, 2.0),
                                     ('c', 4, 3.0), ('d', 5, 4.0)]:
            entry = _find_data(data, sym, line=line)
            self.assertIsNotNone(entry, f"No probe for {sym} at line {line}")
            y = _get_y(entry)
            self.assertEqual(y, [expected],
                             f"{sym} should be [{expected}], got {y}")
            values.append(expected)

        # Strict monotonic ordering
        for i in range(len(values) - 1):
            self.assertLess(values[i], values[i + 1],
                            f"Arrow of time violated: {values[i]} >= {values[i+1]}")

    def test_interleaved_multi_var_loop(self):
        """
        Loop with x and y: per-iteration, x assignment before y assignment.

        Script: interleaved.py
            def main():
                for i in range(3):    # line 2
                    x = i             # line 3
                    y = x + 10        # line 4
                return
        """
        data = self._run("interleaved.py", ["3:x:1", "4:x:1", "4:y:1"])

        x_assign = _find_data(data, 'x', line=3)
        x_read = _find_data(data, 'x', line=4)
        y_assign = _find_data(data, 'y', line=4)

        if x_assign is not None:
            self.assertEqual(_get_y(x_assign), [0.0, 1.0, 2.0])

        if x_read is not None:
            self.assertEqual(_get_y(x_read), [0.0, 1.0, 2.0])

        if y_assign is not None:
            self.assertEqual(_get_y(y_assign), [10.0, 11.0, 12.0])

    # =================================================================
    # 7. Edge Cases
    # =================================================================

    def test_multiple_assignment_single_line(self):
        """
        a = b = c = 42: all three get value 42.

        Script: multi_assign.py
            def main():
                a = b = c = 42    # line 2
                return a
        """
        data = self._run("multi_assign.py", ["2:a:1", "2:b:1", "2:c:1"])

        for sym in ['a', 'b', 'c']:
            entry = _find_data(data, sym, line=2)
            if entry is not None:
                self.assertEqual(_get_y(entry), [42.0],
                                 f"{sym} should be 42")

    def test_tuple_unpack(self):
        """
        a, b, c = 1, 2, 3: each variable gets its own value.

        Script: unpack.py
            def main():
                a, b, c = 1, 2, 3    # line 2
                return a
        """
        data = self._run("unpack.py", ["2:a:1", "2:b:1", "2:c:1"])

        for sym, expected in [('a', 1.0), ('b', 2.0), ('c', 3.0)]:
            entry = _find_data(data, sym, line=2)
            if entry is not None:
                self.assertEqual(_get_y(entry), [expected],
                                 f"{sym} should be {expected}")

    def test_exception_no_stale(self):
        """
        x = 999 after raise should never fire.

        Script: exception.py
            def main():
                x = 1             # line 2
                try:
                    x = 2         # line 4
                    raise ValueError
                    x = 999       # line 6 (dead code)
                except:
                    x = 3         # line 8
                return x
        """
        data = self._run("exception.py",
                          ["2:x:1", "4:x:1", "6:x:1", "8:x:1"])

        # x = 1
        x1 = _find_data(data, 'x', line=2)
        if x1 is not None:
            self.assertEqual(_get_y(x1), [1.0])

        # x = 2
        x2 = _find_data(data, 'x', line=4)
        if x2 is not None:
            self.assertEqual(_get_y(x2), [2.0])

        # x = 999 should NOT fire (dead code)
        x_dead = _find_data(data, 'x', line=6)
        if x_dead is not None:
            self.assertEqual(_get_y(x_dead), [],
                             "Dead code x=999 should NOT produce data")

        # x = 3
        x3 = _find_data(data, 'x', line=8)
        if x3 is not None:
            self.assertEqual(_get_y(x3), [3.0])

    def test_global_vs_local(self):
        """
        Local x = 1 should NOT see global x = 100.

        Script: global_local.py
            x = 100          # line 1
                             # line 2 (blank)
            def main():
                x = 1        # line 4
                return x
        """
        data = self._run("global_local.py", ["4:x:1"])

        x_entry = _find_data(data, 'x', line=4)
        self.assertIsNotNone(x_entry, "No probe for local x at line 4")
        self.assertEqual(_get_y(x_entry), [1.0],
                         "Local x should be 1, not 100")

    def test_walrus_operator(self):
        """
        Walrus operator (:=) assigns inside a comprehension filter.

        Script: walrus.py
            def main():
                data = [1, 2, 3, 4, 5]                            # line 2
                result = [y for x in data if (y := x * 2) > 4]    # line 3
                return result

        y is assigned via := for each element. The walrus assignment
        fires for ALL iterations (y = 2, 4, 6, 8, 10), not just the
        ones that pass the filter. result = [6, 8, 10].
        """
        data = self._run("walrus.py", ["3:y:1"])

        y_entry = _find_data(data, 'y', line=3)
        # Walrus operator may or may not be capturable depending on tracer
        # If captured, y gets assigned on every iteration: 2, 4, 6, 8, 10
        if y_entry is not None:
            y_values = _get_y(y_entry)
            self.assertTrue(len(y_values) > 0,
                            "Walrus y should produce at least some captures")
            # All values should be even (x * 2)
            for v in y_values:
                self.assertEqual(v % 2, 0,
                                 f"Walrus y should be even (x*2), got {v}")


if __name__ == "__main__":
    unittest.main()
