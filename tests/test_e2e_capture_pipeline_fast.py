import json
import os
import re
import subprocess
import sys
import unittest

class TestE2ECapturePipelineFast(unittest.TestCase):
    """Fast End-to-end tests for the capture pipeline using Megascript pattern."""
    
    @classmethod
    def setUpClass(cls):
        """
        Build megascript, run it in one PyProbe process, cache all plot data.
        
        Why build dynamically instead of a static `megascript.py`?
        1. Single Source of Truth: We test the exact `regression/*.py` files on disk.
        2. Line Number Stability: PyProbe requires exact line numbers (e.g., `--probe 4:x:1`). 
           If we used a static file, modifying any early test would shift line numbers for 
           all subsequent tests, breaking their probes. Building dynamically calculates the 
           correct line offsets at runtime so probes always map accurately.
        """
        cls.repo_root = os.getcwd()
        if not os.path.exists(os.path.join(cls.repo_root, 'pyprobe', '__main__.py')):
            raise RuntimeError("Run tests from repo root")
            
        cls.megascript_path = os.path.join(cls.repo_root, "tests", "gui", "data", "e2e_capture_temporal_megascript.py")
        os.makedirs(os.path.dirname(cls.megascript_path), exist_ok=True)
        
        files = {
            "loop": os.path.join(cls.repo_root, "regression", "loop.py"),
            "deferred_return": os.path.join(cls.repo_root, "regression", "deferred_return.py"),
            "high_freq": os.path.join(cls.repo_root, "regression", "high_freq.py"),
            "multi_probe": os.path.join(cls.repo_root, "regression", "multi_probe.py"),
        }
        
        megascript_content = 'import sys\nimport time\n'
        probes = []
        
        current_megascript_line = 3
        
        # Maps of the lines to probe in the original scripts
        lines_to_probe = {
            "loop": [(4, "x", 1)],
            "deferred_return": [(7, "x", 1)],
            "high_freq": [(8, "x", 1)],
            "multi_probe": [(9, "a", 1), (9, "b", 1), (9, "x", 1)]
        }
        
        funcs = []
        for name, path in files.items():
            func_name = f"run_{name}"
            funcs.append(func_name)
            megascript_content += f"def {func_name}():\n"
            current_megascript_line += 1
            
            with open(path, "r") as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines):
                orig_line = i + 1
                if line.startswith("if __name__ =="):
                    megascript_content += "    if True:\n"
                else:
                    megascript_content += "    " + line
                current_megascript_line += 1
                
                for p_line, symbol, inst in lines_to_probe.get(name, []):
                    if p_line == orig_line:
                        # Append mapped probe
                        probes.append(f"{current_megascript_line - 1}:{symbol}:{inst}")
            
            megascript_content += "\n"
            current_megascript_line += 1
            
        megascript_content += "if __name__ == '__main__':\n"
        for f in funcs:
            megascript_content += f"    {f}()\n"
            megascript_content += f"    time.sleep(0.3)\n" # Wait for PLOT_DATA signals to propagate
            
        with open(cls.megascript_path, "w") as f:
            f.write(megascript_content)
            
        # Run PyProbe once on the megascript
        python_exe = sys.executable
        cmd = [
            python_exe, "-m", "pyprobe",
            "--auto-run",
            "--auto-quit",
            "--loglevel", "WARNING",
        ]
        for p in probes:
            cmd.extend(["--probe", p])
        cmd.append(cls.megascript_path)
        
        env = os.environ.copy()
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=20,
        )
        
        cls.megascript_output = result.stdout + result.stderr
        if result.returncode != 0:
            raise RuntimeError(f"PyProbe failed with code {result.returncode}:\n{cls.megascript_output}")
            
        # Parse all PLOT_DATA
        cls.all_plot_data = []
        matches = re.findall(r'PLOT_DATA:(\{.*?\})', cls.megascript_output)
        for match in matches:
            try:
                cls.all_plot_data.append(json.loads(match))
            except json.JSONDecodeError:
                pass
                
    def assertHasPlotData(self, symbol, expected_y):
        for data in self.all_plot_data:
            if data.get('symbol') == symbol and data.get('y') == expected_y:
                return
        
        # If not found, build a helpful error message
        found = [
            f"{d.get('symbol')}: {d.get('y')}"
            for d in self.all_plot_data 
            if d.get('symbol') == symbol
        ]
        self.fail(f"Could not find exact plot data for '{symbol}' with expected values.\n"
                  f"Expected: {expected_y}\n"
                  f"Found sequences for '{symbol}':\n" + str(found) + "\n"
                  f"All plot data emitted:\n{self.all_plot_data}")
            
    def test_loop_values_plotted_correctly(self):
        """Verify loop.py captures x = [9, 8, 7] in Fast Mode."""
        self.assertHasPlotData('x', [9.0, 8.0, 7.0])
        
    def test_deferred_capture_at_function_return(self):
        """Verify deferred_return.py captures x = 42 in Fast Mode."""
        self.assertHasPlotData('x', [42.0])
        
    def test_no_data_loss_high_frequency(self):
        """Verify high_freq.py captures all 100 loop iterations in Fast Mode."""
        expected = [float(i) for i in range(100)]
        self.assertHasPlotData('x', expected)
        
    def test_multi_probe_same_line_plotted(self):
        """Verify multi_probe.py captures a=5, b=3, x=8 in Fast Mode."""
        self.assertHasPlotData('a', [5.0])
        self.assertHasPlotData('b', [3.0])
        self.assertHasPlotData('x', [8.0])

if __name__ == "__main__":
    unittest.main()
