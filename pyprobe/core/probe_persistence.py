"""Probe persistence via sidecar JSON files.

This module provides functions to save and load probe settings (anchors, colors,
lenses, watches, overlays) from a hidden `.pyprobe` directory adjacent to the
target script.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ProbeSpec:
    """Specification for a saved probe."""
    file: str
    line: int
    col: int
    symbol: str
    func: str
    is_assignment: bool
    color: Optional[str] = None
    lens: Optional[str] = None
    
    @classmethod
    def from_anchor(cls, anchor: ProbeAnchor, color: str = None, lens: str = None) -> 'ProbeSpec':
        return cls(
            file=anchor.file,
            line=anchor.line,
            col=anchor.col,
            symbol=anchor.symbol,
            func=anchor.func,
            is_assignment=anchor.is_assignment,
            color=color,
            lens=lens,
        )
    
    def to_anchor(self) -> ProbeAnchor:
        return ProbeAnchor(
            file=self.file,
            line=self.line,
            col=self.col,
            symbol=self.symbol,
            func=self.func,
            is_assignment=self.is_assignment
        )


@dataclass
class WatchSpec:
    """Specification for a saved watch."""
    file: str
    line: int
    col: int
    symbol: str
    func: str
    is_assignment: bool
    
    @classmethod
    def from_anchor(cls, anchor: ProbeAnchor) -> 'WatchSpec':
        return cls(
            file=anchor.file,
            line=anchor.line,
            col=anchor.col,
            symbol=anchor.symbol,
            func=anchor.func,
            is_assignment=anchor.is_assignment,
        )
    
    def to_anchor(self) -> ProbeAnchor:
        return ProbeAnchor(
            file=self.file,
            line=self.line,
            col=self.col,
            symbol=self.symbol,
            func=self.func,
            is_assignment=self.is_assignment
        )


@dataclass
class OverlaySpec:
    """Specification for a saved overlay relationship."""
    target: ProbeSpec
    overlay: ProbeSpec


@dataclass
class ProbeSettings:
    """Complete collection of saved probe settings for a file."""
    probes: List[ProbeSpec] = field(default_factory=list)
    watches: List[WatchSpec] = field(default_factory=list)
    overlays: List[OverlaySpec] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to a JSON-serializable dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProbeSettings':
        """Create settings from a parsed JSON dictionary."""
        settings = cls()
        
        for p in data.get("probes", []):
            try:
                settings.probes.append(ProbeSpec(**p))
            except TypeError as e:
                logger.warning(f"Failed to parse ProbeSpec: {e}")
                
        for w in data.get("watches", []):
            try:
                settings.watches.append(WatchSpec(**w))
            except TypeError as e:
                logger.warning(f"Failed to parse WatchSpec: {e}")
                
        for o in data.get("overlays", []):
            try:
                target = ProbeSpec(**o["target"])
                overlay = ProbeSpec(**o["overlay"])
                settings.overlays.append(OverlaySpec(target=target, overlay=overlay))
            except (TypeError, KeyError) as e:
                logger.warning(f"Failed to parse OverlaySpec: {e}")
                
        return settings


def get_sidecar_path(script_path: str) -> Path:
    """Get the path to the `.pyprobe` sidecar file for a given script.
    
    Creates the hidden `.pyprobe` directory if it doesn't exist.
    """
    script = Path(script_path).resolve()
    sidecar_dir = script.parent / ".pyprobe"
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    
    # Example: my_script.py -> .pyprobe/my_script.py.pyprobe
    return sidecar_dir / f"{script.name}.pyprobe"


def load_probe_settings(script_path: str) -> ProbeSettings:
    """Load probe settings from the sidecar file.
    
    Returns an empty ProbeSettings if the file doesn't exist or is invalid.
    """
    sidecar = get_sidecar_path(script_path)
    if not sidecar.exists():
        return ProbeSettings()
        
    try:
        with open(sidecar, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ProbeSettings.from_dict(data)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load probe settings from {sidecar}: {e}")
        return ProbeSettings()


def save_probe_settings(script_path: str, settings: ProbeSettings) -> None:
    """Save probe settings to the sidecar file."""
    sidecar = get_sidecar_path(script_path)
    
    # If settings are empty, we can just delete the sidecar to keep things clean
    if not settings.probes and not settings.watches and not settings.overlays:
        if sidecar.exists():
            try:
                sidecar.unlink()
                logger.debug(f"Removed empty probe settings file at {sidecar}")
            except OSError as e:
                logger.warning(f"Failed to remove empty probe settings file: {e}")
        return

    try:
        data = settings.to_dict()
        with open(sidecar, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Saved probe settings to {sidecar}")
    except OSError as e:
        logger.error(f"Failed to save probe settings to {sidecar}: {e}")
