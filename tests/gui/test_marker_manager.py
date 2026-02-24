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
