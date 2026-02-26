import time
import pytest
from pyprobe.report.environment import EnvironmentCollector


def test_environment_contains_python_version():
    """Collected env has 'python_version' key with a non-empty string."""
    env = EnvironmentCollector.collect()
    assert "python_version" in env
    assert isinstance(env["python_version"], str)
    assert len(env["python_version"]) > 0


def test_environment_contains_pyprobe_version():
    """Collected env has 'pyprobe_version' matching pyprobe.__version__."""
    import pyprobe
    env = EnvironmentCollector.collect()
    assert "pyprobe_version" in env
    assert env["pyprobe_version"] == pyprobe.__version__


def test_environment_contains_platform():
    """Collected env has 'platform' key with a non-empty string."""
    env = EnvironmentCollector.collect()
    assert "platform" in env
    assert isinstance(env["platform"], str)
    assert len(env["platform"]) > 0


def test_environment_contains_qt_version():
    """Collected env has 'qt_version' key with a non-empty string."""
    env = EnvironmentCollector.collect()
    assert "qt_version" in env
    assert isinstance(env["qt_version"], str)
    assert len(env["qt_version"]) > 0


def test_environment_contains_plugin_list():
    """Collected env has 'plugins' as a list (may be empty)."""
    env = EnvironmentCollector.collect()
    assert "plugins" in env
    assert isinstance(env["plugins"], list)


def test_environment_git_hash_is_string_or_unknown():
    """git_commit_hash is a non-empty string or the literal 'unknown'."""
    env = EnvironmentCollector.collect()
    assert "git_commit_hash" in env
    value = env["git_commit_hash"]
    assert isinstance(value, str)
    assert len(value) > 0


def test_environment_paths_are_sanitized():
    """Any home-directory path in the env snapshot is replaced with <USER_HOME>."""
    from pathlib import Path
    env = EnvironmentCollector.collect()
    full_text = str(env)
    assert str(Path.home()) not in full_text


@pytest.mark.performance
def test_environment_collection_is_fast():
    """EnvironmentCollector.collect() completes in under 2 seconds.

    Marked @pytest.mark.performance — exclude in constrained CI with:
        pytest -m 'not performance'
    """
    start = time.monotonic()
    EnvironmentCollector.collect()
    elapsed = time.monotonic() - start
    assert elapsed < 2.0, f"collect() took {elapsed:.2f}s, expected < 2.0s"
