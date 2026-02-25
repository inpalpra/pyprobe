import pytest
from pyprobe.core.trace_id_manager import TraceIDManager

def test_trace_id_allocation() -> None:
    manager = TraceIDManager()
    
    id0 = manager.allocate("var1")
    id1 = manager.allocate("var2")
    id2 = manager.allocate("var3")
    
    assert id0 == "tr0"
    assert id1 == "tr1"
    assert id2 == "tr2"

def test_trace_id_reuse() -> None:
    manager = TraceIDManager()
    
    manager.allocate("var0") # tr0
    manager.allocate("var1") # tr1
    manager.allocate("var2") # tr2
    
    manager.release("var1")
    
    # Should reuse tr1
    id_new = manager.allocate("var3")
    assert id_new == "tr1"
    
    # Next one should be tr3
    id_next = manager.allocate("var4")
    assert id_next == "tr3"

def test_trace_id_release_and_reallocation_lowest_first() -> None:
    manager = TraceIDManager()
    
    manager.allocate("v0") # tr0
    manager.allocate("v1") # tr1
    manager.allocate("v2") # tr2
    
    manager.release("v0")
    manager.release("v2")
    
    # Lowest available is tr0
    assert manager.allocate("v3") == "tr0"
    # Next lowest is tr2
    assert manager.allocate("v4") == "tr2"
    # Then tr3
    assert manager.allocate("v5") == "tr3"

def test_release_non_existent_variable() -> None:
    manager = TraceIDManager()
    # Should not raise error
    manager.release("unknown")

def test_allocate_same_variable_twice() -> None:
    manager = TraceIDManager()
    id1 = manager.allocate("var1")
    id2 = manager.allocate("var1")
    
    assert id1 == id2 == "tr0"
    assert len(manager.allocated_ids) == 1
