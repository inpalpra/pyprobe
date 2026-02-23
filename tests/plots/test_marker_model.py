import pytest
from pyprobe.plots.marker_model import MarkerType, MarkerShape, MarkerData, MarkerStore

def test_add_remove_marker():
    store = MarkerStore()
    
    signals = []
    store.markers_changed.connect(lambda: signals.append(1))
    
    m0 = store.add_marker('trace_1', 1.0, 2.0)
    assert m0.id == 'm0'
    assert m0.shape == MarkerShape.DIAMOND
    assert len(signals) == 1
    
    m1 = store.add_marker('trace_1', 3.0, 4.0)
    assert m1.id == 'm1'
    assert m1.shape == MarkerShape.TRIANGLE_UP
    assert len(signals) == 2
    
    assert len(store.get_markers()) == 2
    
    store.remove_marker('m0')
    assert len(signals) == 3
    assert len(store.get_markers()) == 1
    assert store.get_marker('m0') is None

def test_update_marker():
    store = MarkerStore()
    m0 = store.add_marker('t', 1.0, 2.0)
    store.update_marker('m0', x=5.0, label='new_label')
    assert m0.x == 5.0
    assert m0.label == 'new_label'

def test_relative_marker():
    store = MarkerStore()
    m0 = store.add_marker('t', 10.0, 20.0)
    m1 = store.add_marker('t', 15.0, 25.0)
    
    store.update_marker('m1', marker_type=MarkerType.RELATIVE, ref_marker_id='m0')
    
    # Check display values (delta)
    dx, dy = store.get_display_values('m1')
    assert dx == 5.0
    assert dy == 5.0
    
    # Update ref marker X, relative marker should move in absolute X
    store.update_marker('m0', x=12.0)
    assert store.get_marker('m0').x == 12.0
    assert store.get_marker('m1').x == 17.0  # shifted by +2.0
    
    # Display delta for m1 should remain the same in X
    dx, dy = store.get_display_values('m1')
    assert dx == 5.0

    # Test removing ref marker clears relative status
    store.remove_marker('m0')
    assert store.get_marker('m1').marker_type == MarkerType.ABSOLUTE
    assert store.get_marker('m1').ref_marker_id is None
