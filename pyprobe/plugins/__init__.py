"""Plugin system for visualization lenses."""
from .base import ProbePlugin
from .registry import PluginRegistry

__all__ = ['ProbePlugin', 'PluginRegistry']
