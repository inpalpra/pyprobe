import pytest
from pyprobe.core.trace_reference_manager import TraceReferenceManager

def test_trace_reference_tracking():
    manager = TraceReferenceManager()
    
    # Add trace tr0 to window w0
    manager.add_reference("tr0", "w0")
    assert manager.get_reference_count("tr0") == 1
    
    # Add trace tr0 to window w1
    manager.add_reference("tr0", "w1")
    assert manager.get_reference_count("tr0") == 2
    
    # Remove reference from w0
    manager.remove_reference("tr0", "w0")
    assert manager.get_reference_count("tr0") == 1
    
    # Remove reference from w1
    manager.remove_reference("tr0", "w1")
    assert manager.get_reference_count("tr0") == 0

def test_unprobe_signal():
    manager = TraceReferenceManager()
    unprobed_ids = []
    
    def on_unprobe(trace_id):
        unprobed_ids.append(trace_id)
        
    manager.unprobe_signal.connect(on_unprobe)
    
    manager.add_reference("tr0", "w0")
    manager.remove_reference("tr0", "w0")
    
    assert "tr0" in unprobed_ids

def test_window_cleanup():
    manager = TraceReferenceManager()
    
    manager.add_reference("tr0", "w0")
    manager.add_reference("tr1", "w0")
    manager.add_reference("tr0", "w1")
    
    assert manager.get_reference_count("tr0") == 2
    assert manager.get_reference_count("tr1") == 1
    
    # Cleanup window w0
    manager.cleanup_window("w0")
    
    assert manager.get_reference_count("tr0") == 1
    assert manager.get_reference_count("tr1") == 0
