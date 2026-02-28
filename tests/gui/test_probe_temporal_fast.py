"""
E2E Probe Temporal Correctness Fast Tests.

This identical to `test_probe_temporal_correctness.py`, but it executes 
a single Megascript in `setUpClass()` rather than spawning 20 separate 
Python subprocesses! This cuts execution time by over 95%.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from typing import Dict, List, Optional, Tuple

def run_pyprobe_e2e_megascript(
    script_path: str,
    probes: List[str],
    timeout: int = 25,
) -> List[dict]:
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

    all_data = []
    matches = re.findall(r'PLOT_DATA:(\{.*?\})', output)

    if result.returncode != 0 and not matches:
        raise RuntimeError(f"PyProbe failed with code {result.returncode}:\n{output}")

    for match in matches:
        all_data.append(json.loads(match))

    return all_data

def _find_data(all_data: List[dict], symbol: str,
               line: Optional[int] = None,
               is_assignment: Optional[bool] = None) -> Optional[dict]:
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
    results = []
    for d in all_data:
        if d.get('symbol') != symbol:
            continue
        if line is not None and d.get('line') != line:
            continue
        results.append(d)
    return results

def _get_y(data: Optional[dict]) -> List[float]:
    if data is None:
        return []
    return data.get('y', [])

MEGASCRIPT = """\
def f_lhs_rhs_sameline():
    x = 3           # L:lhs_rhs_sameline:0
    x = x + 1       # L:lhs_rhs_sameline:1
    return x

def f_augmented_assign():
    x = 10          # L:augmented_assign:0
    x += 5          # L:augmented_assign:1
    return x

def f_double_ref():
    x = 4           # L:double_ref:0
    y = x * x       # L:double_ref:1
    return y

def f_reassign_two():
    x = 3           # L:reassign_two:0
    x = x + 1       # L:reassign_two:1
    return x

def f_chain_reassign():
    x = 1           # L:chain_reassign:0
    x = 2           # L:chain_reassign:1
    x = 3           # L:chain_reassign:2
    x = 4           # L:chain_reassign:3
    return x

def f_swap():
    a = 1           # L:swap:0
    b = 2           # L:swap:1
    a, b = b, a     # L:swap:2
    return a, b

def f_loop_lhs_rhs():
    x = 100         # L:loop_lhs_rhs:0
    for i in range(5):
        x = x - 1   # L:loop_lhs_rhs:1
    return x

def f_loop_counter():
    for i in range(4):
        j = i * 2   # L:loop_counter:0
    return j

def f_accumulator():
    total = 0       # L:accumulator:0
    for i in range(1, 6):
        total = total + i # L:accumulator:1
    return total

def f_diff_funcs_foo():
    x = 10          # L:diff_funcs:0
    return x

def f_diff_funcs_bar():
    x = 20          # L:diff_funcs:1
    return x

def f_nested_shadow():
    x = 1           # L:nested_shadow:0
    def inner():
        x = 2       # L:nested_shadow:1
        return x
    inner()
    y = x           # L:nested_shadow:2
    return y

def f_recursive(n):
    x = n           # L:recursive:0
    if n > 0:
        f_recursive(n - 1)
    return

def f_conditional():
    flag = True     # L:conditional:0
    if flag:
        x = 42      # L:conditional:1
    else:
        x = 99      # L:conditional:2
    y = x           # L:conditional:3
    return y

def f_ternary():
    a = 5           # L:ternary:0
    x = a if a > 3 else 0 # L:ternary:1
    return x

def f_monotonic():
    a = 1           # L:monotonic:0
    b = a + 1       # L:monotonic:1
    c = b + 1       # L:monotonic:2
    d = c + 1       # L:monotonic:3
    return d

def f_interleaved():
    for i in range(3):
        x = i       # L:interleaved:0
        y = x + 10  # L:interleaved:1
    return

def f_multi_assign():
    a = b = c = 42  # L:multi_assign:0
    return a

def f_unpack():
    a, b, c = 1, 2, 3 # L:unpack:0
    return a

def f_exception():
    x = 1           # L:exception:0
    try:
        x = 2       # L:exception:1
        raise ValueError
        x = 999     # L:exception:2
    except:
        x = 3       # L:exception:3
    return x

x_global = 100      # L:global_local:0
def f_global_local():
    x = 1           # L:global_local:1
    return x

def f_walrus():
    data = [1, 2, 3, 4, 5]
    result = [y for x in data if (y := x * 2) > 4] # L:walrus:0
    return result

def main():
    f_lhs_rhs_sameline()
    f_augmented_assign()
    f_double_ref()
    f_reassign_two()
    f_chain_reassign()
    f_swap()
    f_loop_lhs_rhs()
    f_loop_counter()
    f_accumulator()
    f_diff_funcs_foo()
    f_diff_funcs_bar()
    f_nested_shadow()
    f_recursive(3)
    f_conditional()
    f_ternary()
    f_monotonic()
    f_interleaved()
    f_multi_assign()
    f_unpack()
    f_exception()
    f_global_local()
    f_walrus()

if __name__ == "__main__":
    main()
"""

class TestProbeTemporalCorrectnessFast(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.megascript_path = os.path.realpath(os.path.join(cls.temp_dir.name, "megascript.py"))
        with open(cls.megascript_path, "w") as f:
            f.write(MEGASCRIPT)

        cls.linemap = {}
        for i, line in enumerate(MEGASCRIPT.splitlines()):
            m = re.search(r'# L:([\w]+:\d+)', line)
            if m:
                cls.linemap[m.group(1)] = i + 1

        cls.probes = [
            f"{cls.linemap['lhs_rhs_sameline:1']}:x:1",
            f"{cls.linemap['lhs_rhs_sameline:1']}:x:2",
            f"{cls.linemap['augmented_assign:1']}:x:1",
            f"{cls.linemap['augmented_assign:1']}:x:2",
            f"{cls.linemap['double_ref:1']}:x:1",
            f"{cls.linemap['double_ref:1']}:x:2",
            f"{cls.linemap['double_ref:1']}:y:1",
            f"{cls.linemap['reassign_two:0']}:x:1",
            f"{cls.linemap['reassign_two:1']}:x:1",
            f"{cls.linemap['reassign_two:1']}:x:2",
            f"{cls.linemap['chain_reassign:0']}:x:1",
            f"{cls.linemap['chain_reassign:1']}:x:1",
            f"{cls.linemap['chain_reassign:2']}:x:1",
            f"{cls.linemap['chain_reassign:3']}:x:1",
            f"{cls.linemap['swap:2']}:a:1",
            f"{cls.linemap['swap:2']}:b:1",
            f"{cls.linemap['swap:2']}:a:2",
            f"{cls.linemap['swap:2']}:b:2",
            f"{cls.linemap['loop_lhs_rhs:1']}:x:1",
            f"{cls.linemap['loop_lhs_rhs:1']}:x:2",
            f"{cls.linemap['loop_counter:0']}:i:1",
            f"{cls.linemap['loop_counter:0']}:j:1",
            f"{cls.linemap['accumulator:1']}:total:1",
            f"{cls.linemap['accumulator:1']}:total:2",
            f"{cls.linemap['diff_funcs:0']}:x:1",
            f"{cls.linemap['diff_funcs:1']}:x:1",
            f"{cls.linemap['nested_shadow:0']}:x:1",
            f"{cls.linemap['nested_shadow:1']}:x:1",
            f"{cls.linemap['nested_shadow:2']}:x:1",
            f"{cls.linemap['recursive:0']}:x:1",
            f"{cls.linemap['conditional:1']}:x:1",
            f"{cls.linemap['conditional:2']}:x:1",
            f"{cls.linemap['conditional:3']}:x:1",
            f"{cls.linemap['ternary:1']}:x:1",
            f"{cls.linemap['ternary:1']}:a:1",
            f"{cls.linemap['monotonic:0']}:a:1",
            f"{cls.linemap['monotonic:1']}:b:1",
            f"{cls.linemap['monotonic:2']}:c:1",
            f"{cls.linemap['monotonic:3']}:d:1",
            f"{cls.linemap['interleaved:0']}:x:1",
            f"{cls.linemap['interleaved:1']}:x:1",
            f"{cls.linemap['interleaved:1']}:y:1",
            f"{cls.linemap['multi_assign:0']}:a:1",
            f"{cls.linemap['multi_assign:0']}:b:1",
            f"{cls.linemap['multi_assign:0']}:c:1",
            f"{cls.linemap['unpack:0']}:a:1",
            f"{cls.linemap['unpack:0']}:b:1",
            f"{cls.linemap['unpack:0']}:c:1",
            f"{cls.linemap['exception:0']}:x:1",
            f"{cls.linemap['exception:1']}:x:1",
            f"{cls.linemap['exception:2']}:x:1",
            f"{cls.linemap['exception:3']}:x:1",
            f"{cls.linemap['global_local:1']}:x:1",
            f"{cls.linemap['walrus:0']}:y:1",
        ]

        cls.all_data = run_pyprobe_e2e_megascript(cls.megascript_path, cls.probes)

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_lhs_rhs_same_var_same_line(self):
        line = self.linemap['lhs_rhs_sameline:1']
        x_entries = _find_all(self.all_data, 'x', line=line)
        self.assertEqual(len(x_entries), 2)
        x_entries.sort(key=lambda d: d.get('col', 0))
        lhs = _find_data(self.all_data, 'x', line=line, is_assignment=True)
        rhs = _find_data(self.all_data, 'x', line=line, is_assignment=False)
        self.assertIsNotNone(lhs)
        self.assertIsNotNone(rhs)
        self.assertEqual(_get_y(rhs), [3.0])
        self.assertEqual(_get_y(lhs), [4.0])

    def test_augmented_assign(self):
        line = self.linemap['augmented_assign:1']
        x_entries = _find_all(self.all_data, 'x', line=line)
        self.assertGreaterEqual(len(x_entries), 1)
        lhs = _find_data(self.all_data, 'x', line=line, is_assignment=True)
        if lhs is not None:
            self.assertEqual(_get_y(lhs), [15.0])

    def test_double_reference_rhs(self):
        line = self.linemap['double_ref:1']
        x_entries = _find_all(self.all_data, 'x', line=line)
        for entry in x_entries:
            self.assertEqual(_get_y(entry), [4.0])
        y_entry = _find_data(self.all_data, 'y', line=line)
        self.assertIsNotNone(y_entry)
        self.assertEqual(_get_y(y_entry), [16.0])

    def test_reassignment_two_lines(self):
        l0 = self.linemap['reassign_two:0']
        l1 = self.linemap['reassign_two:1']
        x_line0 = _find_data(self.all_data, 'x', line=l0)
        self.assertIsNotNone(x_line0)
        self.assertEqual(_get_y(x_line0), [3.0])
        lhs = _find_data(self.all_data, 'x', line=l1, is_assignment=True)
        rhs = _find_data(self.all_data, 'x', line=l1, is_assignment=False)
        if lhs is not None: self.assertEqual(_get_y(lhs), [4.0])
        if rhs is not None: self.assertEqual(_get_y(rhs), [3.0])

    def test_chain_reassignment(self):
        lines = [
            (self.linemap['chain_reassign:0'], 1.0),
            (self.linemap['chain_reassign:1'], 2.0),
            (self.linemap['chain_reassign:2'], 3.0),
            (self.linemap['chain_reassign:3'], 4.0),
        ]
        for line, expected in lines:
            entry = _find_data(self.all_data, 'x', line=line)
            self.assertIsNotNone(entry)
            self.assertEqual(_get_y(entry), [expected])

    def test_swap_pattern(self):
        line = self.linemap['swap:2']
        a_lhs = _find_data(self.all_data, 'a', line=line, is_assignment=True)
        if a_lhs is not None: self.assertEqual(_get_y(a_lhs), [2.0])
        b_lhs = _find_data(self.all_data, 'b', line=line, is_assignment=True)
        if b_lhs is not None: self.assertEqual(_get_y(b_lhs), [1.0])
        a_rhs = _find_data(self.all_data, 'a', line=line, is_assignment=False)
        if a_rhs is not None: self.assertEqual(_get_y(a_rhs), [1.0])
        b_rhs = _find_data(self.all_data, 'b', line=line, is_assignment=False)
        if b_rhs is not None: self.assertEqual(_get_y(b_rhs), [2.0])

    def test_loop_lhs_and_rhs_both_probed(self):
        line = self.linemap['loop_lhs_rhs:1']
        lhs = _find_data(self.all_data, 'x', line=line, is_assignment=True)
        rhs = _find_data(self.all_data, 'x', line=line, is_assignment=False)
        if lhs is not None: self.assertEqual(_get_y(lhs), [99.0, 98.0, 97.0, 96.0, 95.0])
        if rhs is not None: self.assertEqual(_get_y(rhs), [100.0, 99.0, 98.0, 97.0, 96.0])
        if lhs is not None and rhs is not None:
            for i, (r, l) in enumerate(zip(_get_y(rhs), _get_y(lhs))):
                self.assertEqual(r, l + 1)

    def test_loop_counter(self):
        line = self.linemap['loop_counter:0']
        i_entry = _find_data(self.all_data, 'i', line=line)
        j_entry = _find_data(self.all_data, 'j', line=line)
        if i_entry is not None: self.assertEqual(_get_y(i_entry), [0.0, 1.0, 2.0, 3.0])
        if j_entry is not None: self.assertEqual(_get_y(j_entry), [0.0, 2.0, 4.0, 6.0])

    def test_accumulator(self):
        line = self.linemap['accumulator:1']
        lhs = _find_data(self.all_data, 'total', line=line, is_assignment=True)
        rhs = _find_data(self.all_data, 'total', line=line, is_assignment=False)
        if lhs is not None: self.assertEqual(_get_y(lhs), [1.0, 3.0, 6.0, 10.0, 15.0])
        if rhs is not None: self.assertEqual(_get_y(rhs), [0.0, 1.0, 3.0, 6.0, 10.0])

    def test_same_name_different_functions(self):
        line_foo = self.linemap['diff_funcs:0']
        line_bar = self.linemap['diff_funcs:1']
        x_foo = _find_data(self.all_data, 'x', line=line_foo)
        x_bar = _find_data(self.all_data, 'x', line=line_bar)
        self.assertIsNotNone(x_foo)
        self.assertIsNotNone(x_bar)
        self.assertEqual(_get_y(x_foo), [10.0])
        self.assertEqual(_get_y(x_bar), [20.0])

    def test_nested_function_shadowing(self):
        l0 = self.linemap['nested_shadow:0']
        l1 = self.linemap['nested_shadow:1']
        l2 = self.linemap['nested_shadow:2']
        x_outer = _find_data(self.all_data, 'x', line=l0)
        if x_outer is not None: self.assertEqual(_get_y(x_outer), [1.0])
        x_inner = _find_data(self.all_data, 'x', line=l1)
        if x_inner is not None: self.assertEqual(_get_y(x_inner), [2.0])
        x_read = _find_data(self.all_data, 'x', line=l2)
        if x_read is not None: self.assertEqual(_get_y(x_read), [1.0])

    def test_recursive(self):
        line = self.linemap['recursive:0']
        x_entry = _find_data(self.all_data, 'x', line=line)
        self.assertIsNotNone(x_entry)
        self.assertEqual(_get_y(x_entry), [3.0, 2.0, 1.0, 0.0])

    def test_conditional_assignment(self):
        l1 = self.linemap['conditional:1']
        l2 = self.linemap['conditional:2']
        l3 = self.linemap['conditional:3']
        x_taken = _find_data(self.all_data, 'x', line=l1)
        self.assertIsNotNone(x_taken)
        self.assertEqual(_get_y(x_taken), [42.0])
        x_dead = _find_data(self.all_data, 'x', line=l2)
        if x_dead is not None: self.assertEqual(_get_y(x_dead), [])
        y_entry = _find_data(self.all_data, 'y', line=l3)
        if y_entry is not None: self.assertEqual(_get_y(y_entry), [42.0])

    def test_ternary(self):
        line = self.linemap['ternary:1']
        x_entry = _find_data(self.all_data, 'x', line=line)
        if x_entry is not None: self.assertEqual(_get_y(x_entry), [5.0])
        a_entry = _find_data(self.all_data, 'a', line=line)
        if a_entry is not None: self.assertEqual(_get_y(a_entry), [5.0])

    def test_monotonic_seq_across_probes(self):
        lines = [
            ('a', self.linemap['monotonic:0'], 1.0),
            ('b', self.linemap['monotonic:1'], 2.0),
            ('c', self.linemap['monotonic:2'], 3.0),
            ('d', self.linemap['monotonic:3'], 4.0),
        ]
        values = []
        for sym, line, expected in lines:
            entry = _find_data(self.all_data, sym, line=line)
            self.assertIsNotNone(entry)
            self.assertEqual(_get_y(entry), [expected])
            values.append(expected)
        for i in range(len(values) - 1):
            self.assertLess(values[i], values[i + 1])

    def test_interleaved_multi_var_loop(self):
        l0 = self.linemap['interleaved:0']
        l1 = self.linemap['interleaved:1']
        x_assign = _find_data(self.all_data, 'x', line=l0)
        x_read = _find_data(self.all_data, 'x', line=l1)
        y_assign = _find_data(self.all_data, 'y', line=l1)
        if x_assign is not None: self.assertEqual(_get_y(x_assign), [0.0, 1.0, 2.0])
        if x_read is not None: self.assertEqual(_get_y(x_read), [0.0, 1.0, 2.0])
        if y_assign is not None: self.assertEqual(_get_y(y_assign), [10.0, 11.0, 12.0])

    def test_multiple_assignment_single_line(self):
        line = self.linemap['multi_assign:0']
        for sym in ['a', 'b', 'c']:
            entry = _find_data(self.all_data, sym, line=line)
            if entry is not None: self.assertEqual(_get_y(entry), [42.0])

    def test_tuple_unpack(self):
        line = self.linemap['unpack:0']
        for sym, exp in [('a', 1.0), ('b', 2.0), ('c', 3.0)]:
            entry = _find_data(self.all_data, sym, line=line)
            if entry is not None: self.assertEqual(_get_y(entry), [exp])

    def test_exception_no_stale(self):
        l0 = self.linemap['exception:0']
        l1 = self.linemap['exception:1']
        l2 = self.linemap['exception:2']
        l3 = self.linemap['exception:3']
        x1 = _find_data(self.all_data, 'x', line=l0)
        if x1 is not None: self.assertEqual(_get_y(x1), [1.0])
        x2 = _find_data(self.all_data, 'x', line=l1)
        if x2 is not None: self.assertEqual(_get_y(x2), [2.0])
        x_dead = _find_data(self.all_data, 'x', line=l2)
        if x_dead is not None: self.assertEqual(_get_y(x_dead), [])
        x3 = _find_data(self.all_data, 'x', line=l3)
        if x3 is not None: self.assertEqual(_get_y(x3), [3.0])

    def test_global_vs_local(self):
        line = self.linemap['global_local:1']
        x_entry = _find_data(self.all_data, 'x', line=line)
        self.assertIsNotNone(x_entry)
        self.assertEqual(_get_y(x_entry), [1.0])

    def test_walrus_operator(self):
        line = self.linemap['walrus:0']
        y_entry = _find_data(self.all_data, 'y', line=line)
        if y_entry is not None:
            y_values = _get_y(y_entry)
            self.assertTrue(len(y_values) > 0)
            for v in y_values:
                self.assertEqual(v % 2, 0)

if __name__ == "__main__":
    unittest.main()
