import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidget, QLineEdit, QComboBox
from pyprobe.gui.marker_manager import MarkerManager
from pyprobe.plots.marker_model import MarkerStore, MarkerType

@pytest.fixture
def clean_marker_stores():
    MarkerStore._all_stores.clear()
    MarkerStore._global_used_ids.clear()
    yield
    MarkerStore._all_stores.clear()
    MarkerStore._global_used_ids.clear()

def test_marker_manager_initialization(qtbot, clean_marker_stores):
    # Create some dummy stores
    store1 = MarkerStore(parent=None)
    m1 = store1.add_marker(trace_key=0, x=1.0, y=2.0)
    m1.label = "Test M1"
    
    manager = MarkerManager()
    qtbot.addWidget(manager)
    manager.show()
    
    # Wait for population
    qtbot.waitUntil(lambda: manager.table.rowCount() == 1)
    
    assert manager.table.rowCount() == 1
    
    # Check if data bound correctly
    label_edit = manager.table.cellWidget(0, 2)
    assert isinstance(label_edit, QLineEdit)
    assert label_edit.text() == "Test M1"
    
    # Check if updating the marker updates the table without losing the widget
    # Simulate an external update
    store1.update_marker(m1.id, label="Updated M1")
    
    qtbot.wait(50)

    new_label_edit = manager.table.cellWidget(0, 2)
    assert new_label_edit is label_edit, "Table was fully rebuilt, widgets were destroyed!"
    assert label_edit.text() == "Updated M1"

def test_marker_manager_interactions(qtbot, clean_marker_stores):
    store1 = MarkerStore(parent=None)
    m1 = store1.add_marker(trace_key=0, x=1.0, y=2.0)
    
    manager = MarkerManager()
    qtbot.addWidget(manager)
    manager.show()
    
    qtbot.waitUntil(lambda: manager.table.rowCount() == 1)
    
    # Test editing the X value
    x_spin = manager.table.cellWidget(0, 3)
    x_spin.setValue(5.5)
    
    # Process events to allow the valueChanged signal to propagate to the store
    qtbot.wait(10)
    
    assert store1.get_marker(m1.id).x == 5.5
    
    # Test deleting the marker
    del_btn_container = manager.table.cellWidget(0, 10)
    del_btn = del_btn_container._child_widget
    qtbot.mouseClick(del_btn, Qt.MouseButton.LeftButton)
    
    qtbot.waitUntil(lambda: manager.table.rowCount() == 0)
    assert len(store1.get_markers()) == 0
