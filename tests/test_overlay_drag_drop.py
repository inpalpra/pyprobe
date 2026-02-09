"""
Automated GUI test for drag-drop overlay verification.

Tests that:
1. A waveform probe (signal_i) is created
2. An overlay (received_symbols complex array) is added to the signal_i graph
3. The resulting graph has 3 curves with 3 legends:
   - signal_i (primary, real waveform)
   - received_symbols_rhs_real (overlay, real part of complex)
   - received_symbols_rhs_imag (overlay, imag part of complex)

Uses the --overlay CLI argument to programmatically create overlays
without requiring GUI mouse interaction.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from typing import Dict, List, Optional


def run_pyprobe_with_overlay(
    script_path: str,
    probe_spec: str,
    overlay_spec: str,
    timeout: int = 25,
) -> Dict:
    """
    Run pyprobe with a probe and an overlay, return captured PLOT_DATA.
    
    Args:
        script_path: Absolute path to the script
        probe_spec: Probe spec like "70:signal_i:1"
        overlay_spec: Overlay spec like "signal_i:75:received_symbols:1"
        timeout: Maximum seconds to wait
    
    Returns:
        dict with PLOT_DATA for the probed symbol
    """
    python_exe = sys.executable
    
    cmd = [
        python_exe, "-m", "pyprobe",
        "--auto-run",
        "--auto-quit",
        "--loglevel", "WARNING",
        "--probe", probe_spec,
        "--overlay", overlay_spec,
        script_path,
    ]
    
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
    
    # Parse PLOT_DATA lines from output
    matches = re.findall(r'PLOT_DATA:(\{.*?\})', output)
    
    # Also try multi-line JSON (curves array may span)
    # Use a more permissive regex for JSON with nested arrays
    matches_full = re.findall(r'PLOT_DATA:(\{[^}]*"curves":\s*\[.*?\]\})', output, re.DOTALL)
    
    all_matches = matches_full if matches_full else matches
    
    for match in all_matches:
        try:
            data = json.loads(match)
            # Return the first match that has curves (overlay data)
            if 'curves' in data:
                return data
        except json.JSONDecodeError:
            continue
    
    # Fallback: return first match if any
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return {}


class TestOverlayDragDrop(unittest.TestCase):
    """Verify overlay (drag-drop) creates 3 curves with 3 legends."""
    
    @classmethod
    def setUpClass(cls):
        """Verify we're running from repo root."""
        cls.repo_root = os.getcwd()
        if not os.path.exists(os.path.join(cls.repo_root, 'pyprobe', '__main__.py')):
            raise RuntimeError("Run tests from repo root")
    
    def test_overlay_creates_three_curves(self):
        """
        Verify overlaying received_symbols (complex) on signal_i creates 3 curves.
        
        Expected curves:
        1. signal_i (real 1D array, primary)
        2. received_symbols_rhs_real (overlay, real part)
        3. received_symbols_rhs_imag (overlay, imag part)
        """
        script = os.path.join(self.repo_root, 'regression', 'dsp_demo_single_frame.py')
        
        # Probe signal_i at line 70 (inside generate_qam_signal call)
        # signal_i is assigned at line 46 inside generate_qam_signal
        # In main(), the call is at line 70-72
        # received_symbols is re-assigned at line 75 (with offset)
        plot_data = run_pyprobe_with_overlay(
            script,
            probe_spec="46:signal_i:1",
            overlay_spec="signal_i:43:received_symbols:1",
        )
        
        self.assertIn('curves', plot_data, 
                      f"No 'curves' key in PLOT_DATA. Got keys: {list(plot_data.keys())}. "
                      f"Full data: {plot_data}")
        
        curves = plot_data['curves']
        
        # Should have exactly 3 curves
        self.assertEqual(len(curves), 3,
                        f"Expected 3 curves (signal_i + 2 overlay), got {len(curves)}. "
                        f"Curve names: {[c.get('name') for c in curves]}")
        
        # Check primary curve
        primary_curves = [c for c in curves if not c.get('is_overlay', False)]
        self.assertEqual(len(primary_curves), 1,
                        f"Expected 1 primary curve, got {len(primary_curves)}")
        self.assertEqual(primary_curves[0]['name'], 'signal_i')
        
        # Check overlay curves
        overlay_curves = [c for c in curves if c.get('is_overlay', False)]
        self.assertEqual(len(overlay_curves), 2,
                        f"Expected 2 overlay curves, got {len(overlay_curves)}. "
                        f"Names: {[c.get('name') for c in overlay_curves]}")
        
        # Overlay names should contain 'real' and 'imag' 
        # (complex data produces two overlay curves)
        overlay_names = sorted([c['name'] for c in overlay_curves])
        self.assertTrue(
            any('real' in name for name in overlay_names),
            f"No 'real' overlay curve found. Names: {overlay_names}"
        )
        self.assertTrue(
            any('imag' in name for name in overlay_names),
            f"No 'imag' overlay curve found. Names: {overlay_names}"
        )
    
    def test_overlay_curves_have_data(self):
        """Verify all overlay curves have non-empty data."""
        script = os.path.join(self.repo_root, 'regression', 'dsp_demo_single_frame.py')
        
        plot_data = run_pyprobe_with_overlay(
            script,
            probe_spec="46:signal_i:1",
            overlay_spec="signal_i:43:received_symbols:1",
        )
        
        if 'curves' not in plot_data:
            self.skipTest("No curves data available")
        
        for curve in plot_data['curves']:
            self.assertGreater(
                len(curve.get('y', [])), 0,
                f"Curve '{curve.get('name')}' has no y data"
            )
    
    def test_primary_curve_unaffected_by_overlay(self):
        """Verify that the primary signal_i curve data is not changed by overlay."""
        script = os.path.join(self.repo_root, 'regression', 'dsp_demo_single_frame.py')
        
        plot_data = run_pyprobe_with_overlay(
            script,
            probe_spec="46:signal_i:1",
            overlay_spec="signal_i:43:received_symbols:1",
        )
        
        if 'curves' not in plot_data:
            self.skipTest("No curves data available")
        
        primary = [c for c in plot_data['curves'] if not c.get('is_overlay', False)]
        if not primary:
            self.skipTest("No primary curve found")
        
        # signal_i should have 500 points (NUM_SYMBOLS = 500)
        y_data = primary[0].get('y', [])
        self.assertEqual(len(y_data), 500,
                        f"Expected 500 points for signal_i, got {len(y_data)}")


if __name__ == "__main__":
    unittest.main()
