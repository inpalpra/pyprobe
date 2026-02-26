import stat
import pytest
from pathlib import Path
from pyprobe.report.log_capture import LogCapture


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def temp_log(tmp_path) -> Path:
    """Creates a temp log file populated with synthetic log lines."""
    log = tmp_path / "pyprobe_debug.log"
    lines = [
        "2026-01-01 00:00:01 INFO  Application started\n",
        "2026-01-01 00:00:02 DEBUG Tracer installed\n",
        "2026-01-01 00:00:03 WARNING unexpected None returned\n",
        "2026-01-01 00:00:04 ERROR Plot failed for eq0\n",
        "2026-01-01 00:00:05 INFO  Script ended\n",
        "Traceback (most recent call last):\n",
        '  File "/tmp/script.py", line 10, in run\n',
        "    raise ValueError('bad value')\n",
        "ValueError: bad value\n",
        "2026-01-01 00:00:06 INFO  Recovered\n",
    ]
    log.write_text("".join(lines))
    return log


# ── Line-count tests ──────────────────────────────────────────────────────────

def test_log_capture_returns_last_n_lines(temp_log):
    """capture(log_path, n=5) returns at most 5 lines in raw_lines."""
    snapshot = LogCapture.capture(log_path=str(temp_log), n=5)
    assert snapshot is not None
    assert len(snapshot.raw_lines.splitlines()) <= 5


def test_log_capture_returns_all_when_fewer_than_n(temp_log):
    """If the file has fewer lines than n, all lines are returned."""
    snapshot = LogCapture.capture(log_path=str(temp_log), n=1000)
    assert snapshot is not None
    assert len(snapshot.raw_lines.splitlines()) == 10  # fixture has 10 lines


# ── Edge case tests ───────────────────────────────────────────────────────────

def test_log_capture_empty_file_returns_snapshot_with_empty_content(tmp_path):
    """Empty log file returns a LogSnapshot with empty raw_lines, not None."""
    empty_log = tmp_path / "empty.log"
    empty_log.write_text("")
    snapshot = LogCapture.capture(log_path=str(empty_log))
    assert snapshot is not None
    assert snapshot.raw_lines == ""
    assert snapshot.tracebacks == ()
    assert snapshot.warnings_and_errors == ()


def test_log_capture_missing_file_returns_none():
    """Non-existent log path returns None without raising."""
    snapshot = LogCapture.capture(log_path="/nonexistent/path/pyprobe_debug.log")
    assert snapshot is None


def test_log_capture_does_not_raise_on_permission_error(tmp_path):
    """Unreadable file returns None gracefully; PermissionError is not propagated."""
    locked = tmp_path / "locked.log"
    locked.write_text("some content\n")
    locked.chmod(0o000)  # remove read permission
    try:
        snapshot = LogCapture.capture(log_path=str(locked))
        assert snapshot is None
    finally:
        locked.chmod(stat.S_IRUSR | stat.S_IWUSR)  # restore for cleanup


# ── Sanitization test ─────────────────────────────────────────────────────────

def test_log_capture_sanitizes_paths_in_log_lines(tmp_path):
    """Home paths embedded in log lines are replaced with <USER_HOME>."""
    home = str(Path.home())
    log = tmp_path / "sanitize.log"
    log.write_text(f"ERROR in {home}/repos/pyprobe/tracer.py at line 42\n")
    snapshot = LogCapture.capture(log_path=str(log))
    assert snapshot is not None
    assert home not in snapshot.raw_lines
    assert "<USER_HOME>" in snapshot.raw_lines


# ── Classification tests ──────────────────────────────────────────────────────

def test_log_capture_extracts_tracebacks(temp_log):
    """Lines beginning a traceback block appear in LogSnapshot.tracebacks."""
    snapshot = LogCapture.capture(log_path=str(temp_log))
    assert snapshot is not None
    assert len(snapshot.tracebacks) > 0
    assert any("Traceback" in tb for tb in snapshot.tracebacks)


def test_log_capture_extracts_warnings_and_errors(temp_log):
    """Lines with WARNING or ERROR appear in LogSnapshot.warnings_and_errors."""
    snapshot = LogCapture.capture(log_path=str(temp_log))
    assert snapshot is not None
    assert len(snapshot.warnings_and_errors) >= 2
    levels = " ".join(snapshot.warnings_and_errors)
    assert "WARNING" in levels or "ERROR" in levels
