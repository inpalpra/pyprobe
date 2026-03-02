
import subprocess
import sys
import os
import unittest
import time

class TestCLIAutomation(unittest.TestCase):
    """Test the CLI automation features of PyProbe."""

    def test_auto_run_quit_probe(self):
        """
        Test that --auto-run --auto-quit --probe works correctly.
        
        This test runs the regression/loop.py script with a probe on 'x'.
        It asserts that the application exits automatically (success return code)
        and that data was actually captured and received by the GUI (via trace logs).
        """
        # Path to python executable
        python_exe = sys.executable
        
        # Determine paths relative to this test file
        test_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Path to regression script (now in tests/data)
        script_path = os.path.join(test_dir, 'data', 'loop.py')
        if not os.path.exists(script_path):
            # Fallback for local development if not moved yet
            repo_root = os.path.dirname(test_dir)
            script_path = os.path.join(repo_root, 'regression', 'loop.py')
            if not os.path.exists(script_path):
                self.fail(f"Could not find regression script at {script_path}")

        # Path to pyprobe module
        # If running from repo root, it's in the parent of test_dir
        repo_root = os.path.dirname(test_dir)
        has_local_module = os.path.exists(os.path.join(repo_root, 'pyprobe', '__main__.py'))
        
        # Add repo root to sys.path if we want to use local module
        if has_local_module and repo_root not in sys.path:
            sys.path.insert(0, repo_root)

        # Ensure pyprobe is available
        try:
            import pyprobe
        except ImportError:
            self.fail("Could not find pyprobe module in current directory or installed.")

        # Command to run
        # Use sys.executable to ensure we use the same python as the test runner (crucial for isolated venv)
        cmd = [
            sys.executable, "-m", "pyprobe",
            "--auto-run",
            "--auto-quit",
            "--probe", "4:x:1",
            "--loglevel", "DEBUG",
            "--log-console",
            script_path
        ]

        # Environment (enable trace to debug runner behavior)
        env = os.environ.copy()
        env["PYPROBE_TRACE"] = "1"

        # Use a temporary file to capture output (avoids pipe buffering issues)
        import tempfile
        with tempfile.TemporaryFile(mode='w+') as tmp_out:
            print(f"Running command: {' '.join(cmd)}")
            
            # Run subprocess
            try:
                result = subprocess.run(
                    cmd,
                    stdout=tmp_out,
                    stderr=tmp_out,
                    text=True,
                    env=env,
                    timeout=15
                )
            except subprocess.TimeoutExpired as e:
                self.fail(f"Test timed out! check process")

            # Reset file pointer to read output
            tmp_out.seek(0)
            output = tmp_out.read()

        # Assert clean exit
        self.assertEqual(result.returncode, 0, f"Process failed with code {result.returncode}.\nOutput: {output}")

        # Verify actual plotted data values using pyqtgraph export
        import json
        import re
        
        # Find PLOT_DATA lines in output
        plot_data_matches = re.findall(r'PLOT_DATA:(\{.*?\})', output)
        self.assertTrue(len(plot_data_matches) > 0, "No PLOT_DATA export found in output")
        
        # Parse and verify the data for symbol 'x'
        found_x_data = False
        for match in plot_data_matches:
            data = json.loads(match)
            if data.get('symbol') == 'x':
                found_x_data = True
                # loop.py: x = 10, then x = x - 1 three times
                # Expected captured values: [9, 8, 7]
                expected_y = [9.0, 8.0, 7.0]
                actual_y = data.get('y', [])
                self.assertEqual(
                    actual_y, expected_y,
                    f"Plotted data mismatch. Expected {expected_y}, got {actual_y}"
                )
                break
        
        self.assertTrue(found_x_data, "No PLOT_DATA found for symbol 'x'")

if __name__ == "__main__":
    unittest.main()
