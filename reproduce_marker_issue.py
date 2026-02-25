
import sys
from PyQt6.QtWidgets import QApplication, QComboBox
from PyQt6.QtCore import Qt
from pyprobe.gui.marker_manager import MarkerManager
from pyprobe.plots.marker_model import MarkerStore, MarkerType

def test_relative_marker_interaction():
    app = QApplication(sys.argv)
    
    # Create two markers in a store
    store = MarkerStore(parent=None)
    m1 = store.add_marker(trace_key=0, x=1.0, y=10.0)
    m2 = store.add_marker(trace_key=0, x=2.0, y=20.0)
    
    manager = MarkerManager()
    manager.detailed_chk.setChecked(True) # Ensure detailed view
    manager.show()
    
    # Find row for m2
    row = -1
    for r in range(manager.table.rowCount()):
        id_lbl = manager.table.cellWidget(r, 1)
        if id_lbl and m2.id in id_lbl.text():
            row = r
            break
    
    if row == -1:
        print("Marker 2 not found in table")
        return

    # 1. Change m2 to Relative
    type_toggle_container = manager.table.cellWidget(row, 6)
    type_toggle = type_toggle_container._child_widget
    
    print(f"Initial type of m2: {m2.marker_type}")
    from pyprobe.gui.marker_manager import TypeToggleWidget
    if isinstance(type_toggle, TypeToggleWidget):
        type_toggle.rel_btn.click()
    else:
        print(f"FAILURE: Expected TypeToggleWidget, got {type(type_toggle)}")
        return
    print(f"Type of m2 after selection: {m2.marker_type}")
    
    # Process events to allow QTimer.singleShot(0, ...) to fire
    from PyQt6.QtCore import QTimer, QCoreApplication
    loop = QCoreApplication.instance()
    QTimer.singleShot(100, loop.quit)
    loop.exec()

    # 2. Check if Ref box is enabled
    # Re-fetch because table might have been rebuilt (though _update_existing_rows tries to avoid it)
    # Actually, _update_existing_rows IS called if new_row_ids match.
    ref_box_container = manager.table.cellWidget(row, 7)
    ref_box = ref_box_container._child_widget
    
    print(f"Ref box enabled after event processing: {ref_box.isEnabled()}")
    
    # 3. Check items in Ref box
    items = [ref_box.itemText(i) for i in range(ref_box.count())]
    print(f"Ref box items: {items}")
    
    if len(items) <= 1:
        print("FAILURE: Ref box does not contain other markers!")
    else:
        print("SUCCESS: Ref box contains other markers.")

    # Keep app running for a bit to see UI
    # app.exec()

if __name__ == "__main__":
    test_relative_marker_interaction()
