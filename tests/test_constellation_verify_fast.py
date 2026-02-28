"""
Automated GUI test for constellation data verification.

Tests that the constellation plot correctly captures and displays 
complex array data across multiple loop iterations.

This verifies the fix for the stale value bug where iteration 2
would incorrectly capture the modified value from iteration 1.
"""

import json
import os
import re
import subprocess
import sys
import unittest
from typing import Dict, List, Optional


def run_pyprobe_constellation_test(
    script_path: str,
    probe_spec: str,
    timeout: int = 20,
) -> Dict:
    """
    Run pyprobe with constellation script and return captured plot data.
    
    Args:
        script_path: Absolute path to the script
        probe_spec: Probe spec like "58:received_symbols:1"
        timeout: Maximum seconds to wait
    
    Returns:
        dict with PLOT_DATA for the constellation
    """
    python_exe = sys.executable
    
    cmd = [
        python_exe, "-m", "pyprobe",
        "--auto-run",
        "--auto-quit",
        "--loglevel", "WARNING",
        "--probe", probe_spec,
        script_path,
    ]
    
    env = os.environ.copy()
    
    # Fast test pattern: capture directly to memory instead of tempfile
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    
    # Parse PLOT_DATA lines from combined output
    combined_output = (result.stdout or "") + (result.stderr or "")
    matches = re.findall(r'PLOT_DATA:(\{.*?\})', combined_output)

    # Only raise if no data was captured AND process failed
    if result.returncode != 0 and not matches:
        raise RuntimeError(f"PyProbe failed with code {result.returncode}:\n{combined_output}")
    
    # Return the constellation data (should have real/imag keys)
    for match in matches:
        data = json.loads(match)
        if 'real' in data and 'imag' in data:
            return data
    
    return {}


class TestConstellationDataVerificationFast(unittest.TestCase):
    """Verify constellation plot data matches source values."""
    
    @classmethod
    def setUpClass(cls):
        """Verify we're running from repo root and cache subprocess execution."""
        cls.repo_root = os.getcwd()
        if not os.path.exists(os.path.join(cls.repo_root, 'pyprobe', '__main__.py')):
            raise RuntimeError("Run tests from repo root")
            
        cls.script = os.path.join(cls.repo_root, 'regression', 'constellation_verify.py')
        
        # Probe received_symbols at line 60 (the assignment line)
        # Run exactly once for the class
        cls.plot_data = run_pyprobe_constellation_test(cls.script, "60:received_symbols:1")
        
        # Preload expected data
        cls.expected_data = None
        expected_file = '/tmp/constellation_expected.json'
        if os.path.exists(expected_file):
            with open(expected_file, 'r') as f:
                cls.expected_data = json.load(f)
    
    def test_constellation_values_match_source(self):
        """
        Verify that the constellation plot captures the correct values.
        
        This tests the fix for the stale value bug where loop iteration 2
        would incorrectly show data from iteration 1 (after modification).
        
        The regression script uses a fixed random seed, so we can predict
        the exact statistics.
        """
        plot_data = self.plot_data
        
        self.assertIn('real', plot_data, "No constellation real data found")
        self.assertIn('imag', plot_data, "No constellation imag data found")
        self.assertIn('mean_real', plot_data, "No mean_real statistic found")
        self.assertIn('mean_imag', plot_data, "No mean_imag statistic found")
        
        expected = self.expected_data

        # With history_count >= 2, the PLOT_DATA mean is computed over all
        # captured frames combined (not just the last frame). Compute the
        # expected combined mean across all frames for comparison.
        if expected:
            combined_mean_real = sum(f['mean_real'] for f in expected) / len(expected)
            combined_mean_imag = sum(f['mean_imag'] for f in expected) / len(expected)

            self.assertAlmostEqual(
                plot_data['mean_real'],
                combined_mean_real,
                places=1,
                msg=f"Mean real mismatch: got {plot_data['mean_real']}, expected ~{combined_mean_real}"
            )
            self.assertAlmostEqual(
                plot_data['mean_imag'],
                combined_mean_imag,
                places=1,
                msg=f"Mean imag mismatch: got {plot_data['mean_imag']}, expected ~{combined_mean_imag}"
            )
        
        # Verify we have data (not empty)
        self.assertGreater(len(plot_data['real']), 0, "No real values captured")
        self.assertGreater(len(plot_data['imag']), 0, "No imag values captured")
        
        # Verify data is centered around 0 (QAM constellation)
        # A shifted constellation (the bug) would have mean far from 0
        self.assertLess(abs(plot_data['mean_real']), 1.0, 
                       f"Mean real too large ({plot_data['mean_real']}), may be shifted data")
        self.assertLess(abs(plot_data['mean_imag']), 1.0,
                       f"Mean imag too large ({plot_data['mean_imag']}), may be shifted data")
    
    def test_history_count_shows_all_iterations(self):
        """Verify that the constellation captures data from all iterations."""
        plot_data = self.plot_data
        
        self.assertIn('history_count', plot_data, "No history_count found")
        self.assertGreaterEqual(
            plot_data['history_count'], 2,
            f"Expected at least 2 frames in history, got {plot_data['history_count']}"
        )


if __name__ == "__main__":
    unittest.main()
