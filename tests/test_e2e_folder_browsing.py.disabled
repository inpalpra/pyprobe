"""
End-to-End Folder Browsing Tests — Suite A.

Tests the CLI-level folder-loading behaviour using the same subprocess pattern
as test_e2e_capture_pipeline.py.  The GUI runs as a real subprocess; we inspect
returncode and PLOT_DATA: output lines.

Suite A scenarios:
  A1  Open a folder (no file) — clean exit via --auto-quit-timeout
  A2  Open a folder with --probe args — probes silently ignored, clean exit
  A3  Open regression/folder_test/loop_script.py directly — PLOT_DATA baseline
  A4  Same as A3, regression guard — folder feature must not break file-only flow

Fixture folder: regression/folder_test/
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_pyprobe(
    positional_arg: Optional[str] = None,
    probes: Optional[List[str]] = None,
    auto_run: bool = False,
    auto_quit: bool = False,
    auto_quit_timeout: Optional[float] = None,
    timeout: int = 15,
) -> Tuple[int, str]:
    """
    Run ``python -m pyprobe`` and return ``(returncode, combined_output)``.

    Never raises on non-zero exit — callers inspect ``returncode`` directly.
    Combined stdout + stderr are merged so log lines are visible in failures.
    """
    cmd = [
        sys.executable, "-m", "pyprobe",
        "--loglevel", "WARNING",
    ]

    if auto_run:
        cmd.append("--auto-run")
    if auto_quit:
        cmd.append("--auto-quit")
    if auto_quit_timeout is not None:
        cmd.extend(["--auto-quit-timeout", str(auto_quit_timeout)])
    for probe in (probes or []):
        cmd.extend(["--probe", probe])
    if positional_arg is not None:
        cmd.append(positional_arg)

    env = os.environ.copy()

    with tempfile.TemporaryFile(mode="w+") as tmp_out:
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

    return result.returncode, output


def parse_plot_data(output: str) -> Dict[str, List[float]]:
    """Extract ``PLOT_DATA:{...}`` entries from pyprobe stdout/stderr."""
    plot_data: Dict[str, List[float]] = {}
    for match in re.findall(r"PLOT_DATA:(\{.*?\})", output):
        data = json.loads(match)
        symbol = data.get("symbol")
        y_values = data.get("y", [])
        if symbol:
            if symbol in plot_data:
                plot_data[symbol].extend(y_values)
            else:
                plot_data[symbol] = list(y_values)
    return plot_data


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

class TestE2EFolderBrowsing(unittest.TestCase):
    """Suite A: subprocess E2E tests for folder-open CLI flows."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = os.getcwd()
        if not os.path.exists(os.path.join(cls.repo_root, "pyprobe", "__main__.py")):
            raise RuntimeError("Tests must be run from the repository root.")

        cls.examples_dir = os.path.join(cls.repo_root, "examples")
        cls.folder_test_dir = os.path.join(cls.repo_root, "regression", "folder_test")

        if not os.path.isdir(cls.folder_test_dir):
            raise RuntimeError(
                f"Fixture folder not found: {cls.folder_test_dir}\n"
                "Ensure regression/folder_test/ is present."
            )

    # ------------------------------------------------------------------
    # A1 — open folder only, no script, exits cleanly via timeout
    # ------------------------------------------------------------------

    def test_open_folder_cli_then_file(self):
        """
        A1: ``python -m pyprobe examples/`` exits without crashing.

        Passing a directory as the positional arg opens the folder-browsing
        view.  With no file selected there is nothing to auto-quit on, so we
        rely on ``--auto-quit-timeout`` for a hard-quit after 3 s.
        """
        returncode, output = run_pyprobe(
            positional_arg=self.examples_dir,
            auto_quit_timeout=3.0,
            timeout=10,
        )
        self.assertEqual(
            returncode, 0,
            f"Expected clean exit (0) when opening a folder, got {returncode}.\n"
            f"Output:\n{output}",
        )

    # ------------------------------------------------------------------
    # A2 — folder + --probe args: probes silently ignored
    # ------------------------------------------------------------------

    def test_open_folder_with_probe_ignored(self):
        """
        A2: ``python -m pyprobe --probe 4:x:1 examples/`` ignores probes.

        When only a folder is provided (no file loaded yet), probe specs have
        nothing to attach to.  The app must not crash, and no PLOT_DATA must
        be emitted.
        """
        returncode, output = run_pyprobe(
            positional_arg=self.examples_dir,
            probes=["4:x:1"],
            auto_quit_timeout=3.0,
            timeout=10,
        )
        self.assertEqual(
            returncode, 0,
            f"Expected clean exit (0) with folder + --probe, got {returncode}.\n"
            f"Output:\n{output}",
        )
        plot_data = parse_plot_data(output)
        self.assertEqual(
            plot_data, {},
            f"Expected no PLOT_DATA when no script was run, got: {plot_data}",
        )

    # ------------------------------------------------------------------
    # A3 — open file inside folder_test/ directly, verify probe data
    # ------------------------------------------------------------------

    def test_open_file_in_folder_run_probe(self):
        """
        A3: Open ``regression/folder_test/loop_script.py`` directly.

        Establishes the baseline: probing ``y`` on line 2 yields
        ``[10.0, 20.0, 30.0]``.

        loop_script.py:
            1  def main():
            2      for y in [10, 20, 30]:
            3          pass
            ...
        """
        script = os.path.join(self.folder_test_dir, "loop_script.py")
        returncode, output = run_pyprobe(
            positional_arg=script,
            probes=["2:y:1"],
            auto_run=True,
            auto_quit=True,
            timeout=15,
        )
        self.assertEqual(
            returncode, 0,
            f"PyProbe exited with code {returncode}.\nOutput:\n{output}",
        )
        plot_data = parse_plot_data(output)
        self.assertIn("y", plot_data, f"No PLOT_DATA for 'y'.\nOutput:\n{output}")
        self.assertEqual(
            plot_data["y"],
            [10.0, 20.0, 30.0],
            f"Expected [10.0, 20.0, 30.0], got {plot_data['y']}",
        )

    # ------------------------------------------------------------------
    # A4 — same file via normal file arg: regression guard
    # ------------------------------------------------------------------

    def test_folder_preserves_file_behavior(self):
        """
        A4: Adding folder support must not regress single-file probe flow.

        Opens the same ``loop_script.py`` as A3 and expects identical
        PLOT_DATA output.  Any divergence indicates the folder feature broke
        the default file-only path.
        """
        script = os.path.join(self.folder_test_dir, "loop_script.py")
        returncode, output = run_pyprobe(
            positional_arg=script,
            probes=["2:y:1"],
            auto_run=True,
            auto_quit=True,
            timeout=15,
        )
        self.assertEqual(
            returncode, 0,
            f"PyProbe exited with code {returncode}.\nOutput:\n{output}",
        )
        plot_data = parse_plot_data(output)
        self.assertIn("y", plot_data, f"No PLOT_DATA for 'y'.\nOutput:\n{output}")
        self.assertEqual(
            plot_data["y"],
            [10.0, 20.0, 30.0],
            f"Expected [10.0, 20.0, 30.0], got {plot_data['y']} — "
            "folder feature may have broken single-file flow.",
        )


if __name__ == "__main__":
    unittest.main()
