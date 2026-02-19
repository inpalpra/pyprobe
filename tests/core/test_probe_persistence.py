"""Unit tests for probe persistence logic."""

import json
from pathlib import Path

import pytest

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.probe_persistence import (
    ProbeSpec,
    WatchSpec,
    OverlaySpec,
    ProbeSettings,
    get_sidecar_path,
    load_probe_settings,
    save_probe_settings,
)


@pytest.fixture
def test_anchor():
    return ProbeAnchor(
        file="/test/file.py",
        line=42,
        col=0,
        symbol="foo",
        func="main",
        is_assignment=True
    )


class TestSidecarPath:
    def test_sidecar_path_creation(self, tmp_path):
        script = tmp_path / "my_script.py"
        script.touch()
        
        sidecar = get_sidecar_path(str(script))
        
        # Should be inside .pyprobe adjacent to script
        assert sidecar.parent.name == ".pyprobe"
        assert sidecar.parent.parent == tmp_path
        
        # Name should be script.py.pyprobe
        assert sidecar.name == "my_script.py.pyprobe"


class TestSpecConversion:
    def test_probe_spec_round_trip(self, test_anchor):
        spec = ProbeSpec.from_anchor(test_anchor, color="#123456", lens="Line")
        
        assert spec.symbol == "foo"
        assert spec.color == "#123456"
        assert spec.lens == "Line"
        
        anchor = spec.to_anchor()
        assert anchor == test_anchor

    def test_watch_spec_round_trip(self, test_anchor):
        spec = WatchSpec.from_anchor(test_anchor)
        
        assert spec.symbol == "foo"
        assert not hasattr(spec, "color")
        
        anchor = spec.to_anchor()
        assert anchor == test_anchor


class TestPersistence:
    def test_load_nonexistent_returns_empty(self, tmp_path):
        script = tmp_path / "missing.py"
        settings = load_probe_settings(str(script))
        
        assert isinstance(settings, ProbeSettings)
        assert len(settings.probes) == 0
        assert len(settings.watches) == 0
        assert len(settings.overlays) == 0

    def test_save_and_load_empty_deletes_file(self, tmp_path):
        script = tmp_path / "test.py"
        sidecar = get_sidecar_path(str(script))
        
        # Manually create it
        sidecar.touch()
        assert sidecar.exists()
        
        # Saving empty settings should unlink it
        save_probe_settings(str(script), ProbeSettings())
        assert not sidecar.exists()

    def test_round_trip_probe_and_watch(self, tmp_path, test_anchor):
        script = tmp_path / "code.py"
        
        # Build settings
        probe = ProbeSpec.from_anchor(test_anchor, color="#ffffff")
        watch = WatchSpec.from_anchor(test_anchor)
        settings = ProbeSettings(probes=[probe], watches=[watch])
        
        # Save
        save_probe_settings(str(script), settings)
        sidecar = get_sidecar_path(str(script))
        assert sidecar.exists()
        
        # Load
        loaded = load_probe_settings(str(script))
        assert len(loaded.probes) == 1
        assert len(loaded.watches) == 1
        assert loaded.probes[0].symbol == "foo"
        assert loaded.probes[0].color == "#ffffff"
        assert loaded.watches[0].symbol == "foo"
        
    def test_load_handles_malformed_json_gracefully(self, tmp_path):
        script = tmp_path / "broken.py"
        sidecar = get_sidecar_path(str(script))
        
        with open(sidecar, "w") as f:
            f.write("{ invalid_json ]")
            
        settings = load_probe_settings(str(script))
        assert len(settings.probes) == 0
