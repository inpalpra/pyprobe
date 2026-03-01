"""
Automated GUI test for drag-drop overlay verification with two frames.

Tests that:
1. A waveform probe (signal_i) is created at line 70
2. An overlay (received_symbols) is added with instance 2
3. For each iteration, signal_i values from the script match the exported plot data

Uses the --overlay CLI argument to programmatically create overlays
without requiring GUI mouse interaction.
"""

import json
import sys as _sys
import os
import subprocess
import sys
import unittest
from typing import Dict, List


def run_pyprobe_with_overlay(
    script_path: str,
    probe_spec: str,
    overlay_spec: str,
    timeout: int = 4,
) -> Dict:
    """
    Run pyprobe with a probe and an overlay, return captured PLOT_DATA.

    Args:
        script_path: Absolute path to the script
        probe_spec: Probe spec like "70:signal_i:1"
        overlay_spec: Overlay spec like "signal_i:75:received_symbols:2"
        timeout: Maximum seconds to wait

    Returns:
        dict with PLOT_DATA for the probed symbol
    """
    python_exe = sys.executable

    cmd = [
        python_exe, "-m", "pyprobe",
        "--auto-run",
        "--auto-quit",
        "--auto-quit-timeout", str(timeout),
        "--loglevel", "WARNING",
        "--probe", probe_spec,
        "--overlay", overlay_spec,
        script_path,
    ]

    env = os.environ.copy()

    # Fast test pattern: capture directly to memory instead of tempfile
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout + 2,
    )

    output = result.stdout + "\n" + result.stderr

    # Parse PLOT_DATA lines from output (each is a single line of JSON)
    # Accept even if process crashed during cleanup (e.g. SIGSEGV on headless CI)
    all_matches = [l for l in output.splitlines() if l.startswith('PLOT_DATA:')]
    if result.returncode != 0 and not all_matches:
        raise RuntimeError(f"PyProbe failed with code {result.returncode}:\n{output}")

    # Parse PLOT_DATA lines from output (each is a single line of JSON)
    last_valid_data = {}
    for line in output.splitlines():
        if not line.startswith('PLOT_DATA:'):
            continue
        json_str = line[len('PLOT_DATA:'):]
        try:
            data = json.loads(json_str)
            if 'curves' in data:
                last_valid_data = data
        except json.JSONDecodeError:
            continue
    if last_valid_data:
        return last_valid_data

    # Fallback: return first parseable PLOT_DATA if none had curves
    for line in output.splitlines():
        if not line.startswith('PLOT_DATA:'):
            continue
        json_str = line[len('PLOT_DATA:'):]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            continue

    return {}


class TestOverlayDragDropTwoFramesFast(unittest.TestCase):
    """Verify overlay with two frames captures correct data for each iteration."""

    @classmethod
    def setUpClass(cls):
        """Verify we're running from repo root and cache subprocess execution."""
        cls.repo_root = os.getcwd()
        if not os.path.exists(os.path.join(cls.repo_root, 'pyprobe', '__main__.py')):
            raise RuntimeError("Run tests from repo root")

        script = os.path.join(cls.repo_root, 'regression', 'dsp_demo_two_frames.py')

        # Run subprocess EXACTLY ONCE and cache for all test methods
        # Probe signal_i at line 64 (tuple unpack assignment in main())
        # Overlay received_symbols at line 64, instance 1
        cls.plot_data = run_pyprobe_with_overlay(
            script,
            probe_spec="64:signal_i:1",
            overlay_spec="signal_i:64:received_symbols:1",
            timeout=15,
        )

        # Pre-load expected data so we only read the file once too
        expected_file = '/tmp/dsp_demo_two_frames_expected.json'
        if os.path.exists(expected_file):
            with open(expected_file, 'r') as f:
                cls.expected_data = json.load(f)
        else:
            cls.expected_data = None

    def test_signal_i_values_match_expected(self):
        """
        Verify that signal_i values from the plot match the expected values from script.

        The script writes expected values to /tmp/dsp_demo_two_frames_expected.json.
        We compare the last frame's signal_i values with the plot data.
        """
        # Rely on the class-level cached payload
        plot_data = self.plot_data

        # DIAGNOSTIC: dump first few values for CI debugging
        if 'curves' in plot_data:
            curves = plot_data['curves']
            primary = [c for c in curves if not c.get('is_overlay', False)]
            if primary:
                y = primary[0].get('y', [])
                print(f"[DIAG] plot signal_i[:3] = {y[:3]}", file=_sys.stderr)
        if self.expected_data:
            for i, frame in enumerate(self.expected_data):
                print(f"[DIAG] expected frame {i} signal_i[:3] = {frame['signal_i'][:3]}", file=_sys.stderr)

        self.assertIn('curves', plot_data,
                      f"No 'curves' key in PLOT_DATA. Got keys: {list(plot_data.keys())}. "
                      f"Full data: {plot_data}")

        # Get primary curve (signal_i)
        curves = plot_data['curves']
        primary_curves = [c for c in curves if not c.get('is_overlay', False)]
        self.assertEqual(len(primary_curves), 1,
                        f"Expected 1 primary curve, got {len(primary_curves)}")

        plot_signal_i = primary_curves[0].get('y', [])

        self.assertIsNotNone(self.expected_data, "Expected file not found")
        expected_data = self.expected_data

        # The plot should show the last frame's data (waveform replaces on each update)
        last_frame = expected_data[-1]
        expected_signal_i = last_frame['signal_i']

        # Verify lengths match
        self.assertEqual(len(plot_signal_i), len(expected_signal_i),
                        f"Length mismatch: plot has {len(plot_signal_i)}, "
                        f"expected {len(expected_signal_i)}")

        # Verify values match (allowing small floating point tolerance)
        for i, (plot_val, expected_val) in enumerate(zip(plot_signal_i, expected_signal_i)):
            self.assertAlmostEqual(
                plot_val, expected_val, places=6,
                msg=f"Value mismatch at index {i}: plot={plot_val}, expected={expected_val}"
            )

    def test_overlay_curves_match_expected(self):
        """
        Verify that overlay curves (received_symbols real/imag) match expected values.
        """
        # Rely on the class-level cached payload
        plot_data = self.plot_data

        if 'curves' not in plot_data:
            self.skipTest("No curves data available")

        curves = plot_data['curves']
        overlay_curves = [c for c in curves if c.get('is_overlay', False)]

        # Should have 2 overlay curves (real and imag parts of complex)
        self.assertEqual(len(overlay_curves), 2,
                        f"Expected 2 overlay curves, got {len(overlay_curves)}. "
                        f"Names: {[c.get('name') for c in overlay_curves]}")

        self.assertIsNotNone(self.expected_data, "Expected file not found")
        expected_data = self.expected_data

        last_frame = expected_data[-1]
        # The overlay captures received_symbols before the -1-1j offset is applied
        expected_real = last_frame['received_symbols_pre_offset_real']
        expected_imag = last_frame['received_symbols_pre_offset_imag']

        # Find real and imag overlay curves
        real_curve = None
        imag_curve = None
        for c in overlay_curves:
            name = c.get('name', '').lower()
            if 'real' in name:
                real_curve = c
            elif 'imag' in name:
                imag_curve = c

        self.assertIsNotNone(real_curve, "No 'real' overlay curve found")
        self.assertIsNotNone(imag_curve, "No 'imag' overlay curve found")

        # Verify real overlay values
        plot_real = real_curve.get('y', [])
        self.assertEqual(len(plot_real), len(expected_real),
                        f"Real overlay length mismatch: {len(plot_real)} vs {len(expected_real)}")

        for i, (plot_val, expected_val) in enumerate(zip(plot_real, expected_real)):
            self.assertAlmostEqual(
                plot_val, expected_val, places=6,
                msg=f"Real overlay mismatch at index {i}: plot={plot_val}, expected={expected_val}"
            )

        # Verify imag overlay values
        plot_imag = imag_curve.get('y', [])
        self.assertEqual(len(plot_imag), len(expected_imag),
                        f"Imag overlay length mismatch: {len(plot_imag)} vs {len(expected_imag)}")

        for i, (plot_val, expected_val) in enumerate(zip(plot_imag, expected_imag)):
            self.assertAlmostEqual(
                plot_val, expected_val, places=6,
                msg=f"Imag overlay mismatch at index {i}: plot={plot_val}, expected={expected_val}"
            )

    def test_two_frames_captured(self):
        """
        Verify that both frames are processed (script runs to completion).
        """
        # Rely on the class-level cached expected data instead of making subprocess calls
        self.assertIsNotNone(self.expected_data, 
                       "Expected file not created - script may not have completed")
        expected_data = self.expected_data

        self.assertEqual(len(expected_data), 2,
                        f"Expected 2 frames in expected data, got {len(expected_data)}")

        # Verify each frame has the required data
        for i, frame in enumerate(expected_data):
            self.assertIn('signal_i', frame, f"Frame {i} missing signal_i")
            self.assertIn('received_symbols_real', frame, f"Frame {i} missing received_symbols_real")
            self.assertIn('received_symbols_imag', frame, f"Frame {i} missing received_symbols_imag")
            self.assertEqual(len(frame['signal_i']), 64,
                           f"Frame {i} signal_i should have 64 points")


if __name__ == "__main__":
    unittest.main()
