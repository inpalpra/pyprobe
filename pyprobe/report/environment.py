import platform
import subprocess
import sys
from typing import Any

from pyprobe.report.sanitizer import PathSanitizer


class EnvironmentCollector:
    """Gathers system environment data for bug reports."""

    @classmethod
    def collect(cls) -> dict[str, Any]:
        """Collect environment information and return as a sanitized dict."""
        data: dict[str, Any] = {}

        data["python_version"] = PathSanitizer.sanitize(sys.version)

        import pyprobe
        data["pyprobe_version"] = pyprobe.__version__

        data["platform"] = platform.system()

        try:
            from PyQt6.QtCore import QT_VERSION_STR
            data["qt_version"] = QT_VERSION_STR
        except Exception:
            data["qt_version"] = "unknown"

        try:
            from pyprobe.plugins.registry import PluginRegistry
            registry = PluginRegistry.instance()
            data["plugins"] = [p.name for p in registry.all_plugins]
        except Exception:
            data["plugins"] = []

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5
            )
            data["git_commit_hash"] = result.stdout.strip() or "unknown"
        except Exception:
            data["git_commit_hash"] = "unknown"

        sanitized = {
            k: PathSanitizer.sanitize(v) if isinstance(v, str) else v
            for k, v in data.items()
        }
        return sanitized
