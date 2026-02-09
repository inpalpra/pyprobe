
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
        
        # Path to pyprobe module (assuming run from repo root)
        # We need to make sure we're running the module from the current repo
        cwd = os.getcwd()
        if not os.path.exists(os.path.join(cwd, 'pyprobe', '__main__.py')):
            self.fail("Could not find pyprobe module in current directory. Run from repo root.")

        # Path to regression script
        script_path = os.path.join(cwd, 'regression', 'loop.py')
        if not os.path.exists(script_path):
            self.fail(f"Could not find regression script at {script_path}")

        # Command to run
        cmd = [
            python_exe, "-m", "pyprobe",
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

        # Verify output contains key events
        
        # 1. Verify script finished
        self.assertIn("DATA_SCRIPT_END sent successfully", output, "Script did not finish properly")
        
        
        # 3. Verify GUI received data (End-to-End verification)
        self.assertIn("DEBUG: MainWindow received data for x", output, "GUI did not receive probe data for x")

if __name__ == "__main__":
    unittest.main()
