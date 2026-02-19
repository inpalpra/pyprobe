"""Phase 2.6: Plugin registry tests.

Verifies plugin discovery, default selection, and compatibility queries.
"""

import pytest
from pyprobe.plugins.registry import PluginRegistry
from pyprobe.plugins.builtins.waveform import WaveformPlugin
from pyprobe.plugins.builtins.constellation import ConstellationPlugin
from pyprobe.plugins.builtins.scalar_history import ScalarHistoryPlugin
from pyprobe.plugins.builtins.scalar_display import ScalarDisplayPlugin
from pyprobe.core.data_classifier import (
    DTYPE_ARRAY_1D, DTYPE_ARRAY_COMPLEX, DTYPE_SCALAR, DTYPE_ARRAY_2D
)


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset singleton between tests to avoid cross-test contamination."""
    PluginRegistry._instance = None
    yield
    PluginRegistry._instance = None


class TestPluginDiscovery:
    def test_builtins_registered(self):
        """All builtin plugins are discovered and registered."""
        registry = PluginRegistry.instance()
        names = [p.name for p in registry.all_plugins]
        assert "Waveform" in names
        assert "Constellation" in names
        assert "History" in names
        assert "Value" in names

    def test_at_least_four_builtins(self):
        """At least 4 builtin plugins registered."""
        registry = PluginRegistry.instance()
        assert len(registry.all_plugins) >= 4


class TestDefaultPlugin:
    def test_default_array_1d(self):
        """Default plugin for array_1d is Waveform."""
        registry = PluginRegistry.instance()
        plugin = registry.get_default_plugin(DTYPE_ARRAY_1D)
        assert plugin is not None
        assert isinstance(plugin, WaveformPlugin)

    def test_default_complex(self):
        """Default plugin for array_complex is Constellation."""
        registry = PluginRegistry.instance()
        plugin = registry.get_default_plugin(DTYPE_ARRAY_COMPLEX)
        assert plugin is not None
        assert isinstance(plugin, ConstellationPlugin)

    def test_default_scalar(self):
        """Default plugin for scalar is History (higher priority)."""
        registry = PluginRegistry.instance()
        plugin = registry.get_default_plugin(DTYPE_SCALAR)
        assert plugin is not None
        assert isinstance(plugin, ScalarHistoryPlugin)

    def test_unknown_dtype_returns_none(self):
        """Unknown dtype returns None."""
        registry = PluginRegistry.instance()
        assert registry.get_default_plugin("completely_bogus") is None


class TestCompatiblePlugins:
    def test_scalar_has_both(self):
        """Scalar has both History and Value plugins."""
        registry = PluginRegistry.instance()
        plugins = registry.get_compatible_plugins(DTYPE_SCALAR)
        names = [p.name for p in plugins]
        assert "History" in names
        assert "Value" in names

    def test_array_1d_includes_waveform(self):
        """array_1d includes Waveform plugin."""
        registry = PluginRegistry.instance()
        plugins = registry.get_compatible_plugins(DTYPE_ARRAY_1D)
        names = [p.name for p in plugins]
        assert "Waveform" in names

    def test_sorted_by_priority(self):
        """Compatible plugins are sorted by priority descending."""
        registry = PluginRegistry.instance()
        plugins = registry.get_compatible_plugins(DTYPE_SCALAR)
        for i in range(len(plugins) - 1):
            assert plugins[i].priority >= plugins[i+1].priority


class TestPluginByName:
    def test_get_by_name(self):
        """get_plugin_by_name returns correct plugin."""
        registry = PluginRegistry.instance()
        plugin = registry.get_plugin_by_name("Waveform")
        assert isinstance(plugin, WaveformPlugin)

    def test_get_nonexistent_returns_none(self):
        """Nonexistent name returns None."""
        registry = PluginRegistry.instance()
        assert registry.get_plugin_by_name("FooBarPlugin") is None
