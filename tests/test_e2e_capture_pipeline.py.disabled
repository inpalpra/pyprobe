"""
End-to-End Capture Pipeline Tests.

These tests verify that the capture pipeline works correctly from tracer
to actual plotted values in the GUI, using the PLOT_DATA export mechanism.

Architecture success metrics verified:
1. No Data Loss: All captured values visible in graph
2. Correct Ordering: Values appear in execution order
3. Boundary Handling: Captures not lost at function returns
4. Multi-Probe Consistency: Same-line probes maintain logical order
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from typing import Dict, List, Optional


def run_pyprobe_and_get_plot_data(
    script_path: str,
    probes: List[str],
    timeout: int = 15,
) -> Dict[str, List[float]]:
    """
    Run pyprobe with --auto-run --auto-quit and return captured plot data.
    
    Args:
        script_path: Absolute path to the script to run
        probes: List of probe specs like "4:x:1" (line:symbol:instance)
        timeout: Maximum seconds to wait
    
    Returns:
        dict mapping symbol -> list of y values
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
    
    # Parse PLOT_DATA lines
    plot_data: Dict[str, List[float]] = {}
    matches = re.findall(r'PLOT_DATA:(\{.*?\})', output)
    
    for match in matches:
        data = json.loads(match)
        symbol = data.get('symbol')
        y_values = data.get('y', [])
        if symbol:
            if symbol in plot_data:
                plot_data[symbol].extend(y_values)
            else:
                plot_data[symbol] = list(y_values)
    
    return plot_data


class TestE2ECapturePipeline(unittest.TestCase):
    """End-to-end tests for the capture pipeline."""
    
    @classmethod
    def setUpClass(cls):
        """Verify we're running from repo root."""
        cls.repo_root = os.getcwd()
        if not os.path.exists(os.path.join(cls.repo_root, 'pyprobe', '__main__.py')):
            raise RuntimeError("Run tests from repo root")
    
    def test_loop_values_plotted_correctly(self):
        """
        Verify loop.py captures x = [9, 8, 7].
        
        Tests: No Data Loss, Correct Ordering
        """
        script = os.path.join(self.repo_root, 'regression', 'loop.py')
        
        plot_data = run_pyprobe_and_get_plot_data(script, ["4:x:1"])
        
        self.assertIn('x', plot_data, "No plot data for symbol 'x'")
        self.assertEqual(
            plot_data['x'], [9.0, 8.0, 7.0],
            f"Expected [9.0, 8.0, 7.0], got {plot_data['x']}"
        )
    
    def test_deferred_capture_at_function_return(self):
        """
        Verify deferred_return.py captures x = 42 even at function boundary.
        
        Tests: Boundary Handling
        """
        script = os.path.join(self.repo_root, 'regression', 'deferred_return.py')
        
        plot_data = run_pyprobe_and_get_plot_data(script, ["7:x:1"])
        
        self.assertIn('x', plot_data, "No plot data for symbol 'x'")
        self.assertEqual(
            plot_data['x'], [42.0],
            f"Expected [42.0], got {plot_data['x']}"
        )
    
    def test_no_data_loss_high_frequency(self):
        """
        Verify high_freq.py captures all 100 loop iterations.
        
        Tests: No Data Loss
        """
        script = os.path.join(self.repo_root, 'regression', 'high_freq.py')
        
        plot_data = run_pyprobe_and_get_plot_data(script, ["8:x:1"])
        
        self.assertIn('x', plot_data, "No plot data for symbol 'x'")
        
        # Should have exactly 100 values
        self.assertEqual(
            len(plot_data['x']), 100,
            f"Expected 100 values, got {len(plot_data['x'])}"
        )
        
        # Values should be 0-99 in order
        expected = [float(i) for i in range(100)]
        self.assertEqual(
            plot_data['x'], expected,
            f"Values not in expected order"
        )
    
    def test_multi_probe_same_line_plotted(self):
        """
        Verify multi_probe.py captures a=5, b=3, x=8 for same-line probes.
        
        Tests: Multi-Probe Consistency
        """
        script = os.path.join(self.repo_root, 'regression', 'multi_probe.py')
        
        # Probe the line: x = a + b (line 9)
        # a is RHS at col ~8, b is RHS at col ~12, x is LHS at col ~4
        plot_data = run_pyprobe_and_get_plot_data(
            script,
            ["9:a:1", "9:b:1", "9:x:1"]
        )
        
        # Verify each symbol captured correct value
        self.assertIn('a', plot_data, "No plot data for symbol 'a'")
        self.assertIn('b', plot_data, "No plot data for symbol 'b'")
        self.assertIn('x', plot_data, "No plot data for symbol 'x'")
        
        self.assertEqual(plot_data['a'], [5.0], f"Expected a=[5.0], got {plot_data['a']}")
        self.assertEqual(plot_data['b'], [3.0], f"Expected b=[3.0], got {plot_data['b']}")
        self.assertEqual(plot_data['x'], [8.0], f"Expected x=[8.0], got {plot_data['x']}")


if __name__ == "__main__":
    unittest.main()
