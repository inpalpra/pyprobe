import pytest
from PyQt6.QtGui import QColor
from pyprobe.gui.probe_registry import ProbeRegistry
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.gui.probe_controller import ProbeController
from pyprobe.gui.panel_container import ProbePanelContainer
from pyprobe.gui.scalar_watch_window import ScalarWatchSidebar
from pyprobe.gui.probe_panel import ProbePanel
from PyQt6.QtWidgets import QLabel

def test_registry_assigns_ids(qapp):
    registry = ProbeRegistry()
    anchor0 = ProbeAnchor(file="f1.py", line=10, col=0, symbol="x")
    anchor1 = ProbeAnchor(file="f1.py", line=20, col=0, symbol="y")
    
    registry.add_probe(anchor0)
    registry.add_probe(anchor1)
    
    assert registry.get_trace_id(anchor0) == "tr0"
    assert registry.get_trace_id(anchor1) == "tr1"
    
    registry.remove_probe(anchor0)
    anchor2 = ProbeAnchor(file="f1.py", line=30, col=0, symbol="z")
    registry.add_probe(anchor2)
    
    assert registry.get_trace_id(anchor2) == "tr0" # Reused

def test_panel_header_shows_id(qapp):
    anchor = ProbeAnchor(file="f1.py", line=10, col=0, symbol="x")
    panel = ProbePanel(anchor, QColor("red"), "real_1d", trace_id="tr42")
    
    assert panel._id_label.text() == "tr42"

def test_watch_sidebar_shows_id(qapp):
    sidebar = ScalarWatchSidebar()
    anchor = ProbeAnchor(file="f1.py", line=10, col=0, symbol="x")
    sidebar.add_scalar(anchor, QColor("red"), "tr7")
    
    # Find the id label in the sidebar
    found = False
    for i in range(sidebar._content_layout.count()):
        widget = sidebar._content_layout.itemAt(i).widget()
        if widget and widget.objectName() == "scalarCard":
            # Check for id_label in card
            labels = widget.findChildren(QLabel)
            for lbl in labels:
                if lbl.text() == "tr7":
                    found = True
                    break
    
    # Wait, findChildren is better
    labels = sidebar.findChildren(QLabel)
    texts = [l.text() for l in labels]
    print(f"Labels found: {texts}")
    assert "tr7" in texts
