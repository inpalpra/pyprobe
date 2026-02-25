import pytest
from pyprobe.core.window_id_manager import WindowIDManager

def test_window_id_allocation():
    manager = WindowIDManager()
    
    id0 = manager.allocate()
    assert id0 == "w0"
    
    id1 = manager.allocate()
    assert id1 == "w1"
    
    id2 = manager.allocate()
    assert id2 == "w2"

def test_window_id_release_and_reuse():
    manager = WindowIDManager()
    
    id0 = manager.allocate()  # w0
    id1 = manager.allocate()  # w1
    
    manager.release(id0)
    
    id2 = manager.allocate()
    assert id2 == "w0"  # Should reuse w0

def test_window_id_out_of_order_release():
    manager = WindowIDManager()
    
    id0 = manager.allocate()  # w0
    id1 = manager.allocate()  # w1
    id2 = manager.allocate()  # w2
    
    manager.release(id1)
    
    id3 = manager.allocate()
    assert id3 == "w1"  # Should reuse w1
    
    id4 = manager.allocate()
    assert id4 == "w3"  # Should pick next new one
