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

def test_marker_manager_relative_selection(qtbot, clean_marker_stores):
    store = MarkerStore(parent=None)
    m1 = store.add_marker(trace_key=0, x=1.0, y=10.0)
    m2 = store.add_marker(trace_key=0, x=2.0, y=20.0)
    
    manager = MarkerManager()
    qtbot.addWidget(manager)
    manager.detailed_chk.setChecked(True)
    manager.show()
    
    qtbot.waitUntil(lambda: manager.table.rowCount() == 2)
    
    # m2 is row 1 (m1 is m0, m2 is m1 internally often, but let's check labels)
    row_m2 = -1
    for r in range(2):
        if m2.id in manager.table.cellWidget(r, 1).text():
            row_m2 = r
            break
            
    # Click "Rel" button in TypeToggleWidget
    toggle_container = manager.table.cellWidget(row_m2, 6)
    from pyprobe.gui.marker_manager import TypeToggleWidget
    toggle = toggle_container._child_widget
    assert isinstance(toggle, TypeToggleWidget)
    
    qtbot.mouseClick(toggle.rel_btn, Qt.MouseButton.LeftButton)
    assert store.get_marker(m2.id).marker_type == MarkerType.RELATIVE
    
    # Check that ref_box is now enabled
    ref_container = manager.table.cellWidget(row_m2, 7)
    ref_box = ref_container._child_widget
    assert ref_box.isEnabled()
    
    # Select m1 as reference
    idx = ref_box.findText(m1.id)
    ref_box.setCurrentIndex(idx)
    
    qtbot.wait(10)
    assert store.get_marker(m2.id).ref_marker_id == m1.id
