import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from pyprobe.plugins.builtins.waveform import WaveformWidget
from pyprobe.plots.marker_model import MarkerType

def test_markers_gui_waveform(qtbot):
    widget = WaveformWidget("Test", QColor("#ffffff"))
    qtbot.addWidget(widget)
    
    # Needs to be shown for layout and scene to work properly
    with qtbot.waitExposed(widget):
        widget.show()
    
    # Feed data
    widget.update_data(list(range(100)), "float")
    
    # Add marker programmatically
    store = widget._marker_store
    m0 = store.add_marker(0, 10.0, 10.0)
    
    # Force process events just in case
    qtbot.waitUntil(lambda: len(widget._marker_glyphs) == 1)
    
    assert len(store.get_markers()) == 1
    assert m0.id == 'm0'
    
    # Check glyphs
    assert len(widget._marker_glyphs) == 1
    
    # Check overlay text
    overlay = widget._marker_overlay
    assert 'm0' in overlay.labels
    assert overlay.isVisible()
    
    # Remove marker
    store.remove_marker('m0')
    qtbot.waitUntil(lambda: len(widget._marker_glyphs) == 0)
    assert len(store.get_markers()) == 0
    assert not overlay.isVisible()
