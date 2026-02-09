"""Unit tests for CodeViewer probe highlight reference counting."""

import pytest
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor

from pyprobe.gui.code_viewer import CodeViewer
from pyprobe.core.anchor import ProbeAnchor


@pytest.fixture(scope="module")
def app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def code_viewer(app):
    """Create a fresh CodeViewer instance for each test."""
    viewer = CodeViewer()
    yield viewer
    viewer.deleteLater()


@pytest.fixture
def sample_anchor():
    """Create a sample ProbeAnchor for testing."""
    return ProbeAnchor(
        file="/test/script.py",
        line=10,
        col=4,
        symbol="test_var",
        func="test_func",
        is_assignment=False
    )


class TestProbeHighlightRefCounting:
    """Tests for probe highlight reference counting behavior."""

    def test_single_probe_add_creates_highlight(self, code_viewer, sample_anchor):
        """Adding a single probe should create a highlight."""
        color = QColor("#00ff00")
        code_viewer.set_probe_active(sample_anchor, color)
        
        assert sample_anchor in code_viewer._active_probes
        stored_color, ref_count = code_viewer._active_probes[sample_anchor]
        assert ref_count == 1
        assert stored_color.name() == color.name()

    def test_single_probe_remove_clears_highlight(self, code_viewer, sample_anchor):
        """Removing the only probe should clear the highlight."""
        color = QColor("#00ff00")
        code_viewer.set_probe_active(sample_anchor, color)
        code_viewer.remove_probe(sample_anchor)
        
        assert sample_anchor not in code_viewer._active_probes

    def test_two_probes_increment_ref_count(self, code_viewer, sample_anchor):
        """Adding two probes of same anchor should increment ref count to 2."""
        color1 = QColor("#00ff00")
        color2 = QColor("#ff0000")
        
        code_viewer.set_probe_active(sample_anchor, color1)
        code_viewer.set_probe_active(sample_anchor, color2)
        
        assert sample_anchor in code_viewer._active_probes
        stored_color, ref_count = code_viewer._active_probes[sample_anchor]
        assert ref_count == 2
        # Should keep the original color, not the second one
        assert stored_color.name() == color1.name()

    def test_remove_one_of_two_keeps_highlight(self, code_viewer, sample_anchor):
        """Removing one of two probes should decrement count but keep highlight."""
        color = QColor("#00ff00")
        
        # Add two probes
        code_viewer.set_probe_active(sample_anchor, color)
        code_viewer.set_probe_active(sample_anchor, color)
        
        # Remove one
        code_viewer.remove_probe(sample_anchor)
        
        # Highlight should still exist with ref count 1
        assert sample_anchor in code_viewer._active_probes
        stored_color, ref_count = code_viewer._active_probes[sample_anchor]
        assert ref_count == 1

    def test_remove_both_clears_highlight(self, code_viewer, sample_anchor):
        """Removing both probes should clear the highlight entirely."""
        color = QColor("#00ff00")
        
        # Add two probes
        code_viewer.set_probe_active(sample_anchor, color)
        code_viewer.set_probe_active(sample_anchor, color)
        
        # Remove both
        code_viewer.remove_probe(sample_anchor)
        code_viewer.remove_probe(sample_anchor)
        
        # Highlight should be gone
        assert sample_anchor not in code_viewer._active_probes

    def test_remove_unknown_anchor_is_safe(self, code_viewer, sample_anchor):
        """Removing an anchor that was never added should not raise."""
        # Should not raise
        code_viewer.remove_probe(sample_anchor)
        assert sample_anchor not in code_viewer._active_probes

    def test_extra_remove_after_cleared_is_safe(self, code_viewer, sample_anchor):
        """Removing more times than added should not raise."""
        color = QColor("#00ff00")
        
        code_viewer.set_probe_active(sample_anchor, color)
        code_viewer.remove_probe(sample_anchor)
        # Extra remove should be safe
        code_viewer.remove_probe(sample_anchor)
        
        assert sample_anchor not in code_viewer._active_probes

    def test_clear_all_probes_clears_everything(self, code_viewer, sample_anchor):
        """clear_all_probes should remove all highlights regardless of ref count."""
        color = QColor("#00ff00")
        
        # Add multiple refs
        code_viewer.set_probe_active(sample_anchor, color)
        code_viewer.set_probe_active(sample_anchor, color)
        code_viewer.set_probe_active(sample_anchor, color)
        
        code_viewer.clear_all_probes()
        
        assert sample_anchor not in code_viewer._active_probes
        assert len(code_viewer._active_probes) == 0
