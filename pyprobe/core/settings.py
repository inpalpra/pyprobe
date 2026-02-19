"""Persistent application settings helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SETTINGS_DIR = Path.home() / ".config" / "pyprobe"
SETTINGS_PATH = SETTINGS_DIR / "settings.json"


def load_settings() -> dict:
    """Load settings from disk.

    Returns an empty dict if settings file does not exist or contains invalid JSON.
    """
    if not SETTINGS_PATH.exists():
        return {}

    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def save_settings(data: dict) -> None:
    """Persist settings to disk atomically."""
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = SETTINGS_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(SETTINGS_PATH)


def get_setting(key: str, default: Any = None) -> Any:
    """Read a setting value with a fallback default."""
    settings = load_settings()
    return settings.get(key, default)


def set_setting(key: str, value: Any) -> None:
    """Set and persist a single setting key."""
    settings = load_settings()
    settings[key] = value
    save_settings(settings)
