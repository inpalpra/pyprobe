from pathlib import Path
import os
from pyprobe.report.sanitizer import PathSanitizer


def test_sanitize_unix_home_in_path():
    """Absolute Unix home path is replaced with <USER_HOME>."""
    home = str(Path.home())
    result = PathSanitizer.sanitize(f"{home}/repos/pyprobe/script.py")
    assert "<USER_HOME>" in result
    assert home not in result


def test_sanitize_windows_home_in_path():
    """Home path replacement works on all platforms regardless of separator style."""
    home = str(Path.home())
    text = f"File at {home}\\Documents\\file.py"
    result = PathSanitizer.sanitize(text)
    assert home not in result


def test_sanitize_does_not_alter_non_home_paths():
    """Paths outside the home directory are left unchanged."""
    text = "/tmp/pyprobe_debug.log"
    assert PathSanitizer.sanitize(text) == text


def test_sanitize_multiple_occurrences_in_one_string():
    """All occurrences of the home path in a multi-line string are replaced."""
    home = str(Path.home())
    text = f"File: {home}/a.py\nOther: {home}/b.py"
    result = PathSanitizer.sanitize(text)
    assert result.count("<USER_HOME>") == 2
    assert home not in result


def test_sanitize_empty_string_returns_empty():
    """Empty input returns empty output."""
    assert PathSanitizer.sanitize("") == ""


def test_sanitize_path_with_tilde_expansion():
    """Paths expanded from ~ are sanitized."""
    expanded = os.path.expanduser("~/repos/pyprobe")
    result = PathSanitizer.sanitize(expanded)
    assert str(Path.home()) not in result


def test_sanitize_preserves_relative_paths():
    """Relative paths are not modified."""
    text = "examples/dsp_demo.py"
    assert PathSanitizer.sanitize(text) == text


def test_sanitize_in_traceback_string():
    """Home path embedded inside a mock traceback string is sanitized."""
    home = str(Path.home())
    traceback = (
        f'  File "{home}/repos/pyprobe/pyprobe/core/tracer.py", line 42, in trace\n'
        f'    raise ValueError("bad")\n'
        f'ValueError: bad'
    )
    result = PathSanitizer.sanitize(traceback)
    assert home not in result
    assert "<USER_HOME>" in result
