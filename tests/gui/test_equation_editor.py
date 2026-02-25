import pytest
from PyQt6.QtCore import Qt
from pyprobe.gui.equation_editor import EquationEditorDialog
from pyprobe.core.equation_manager import EquationManager

def test_equation_editor_opens(qapp):
    manager = EquationManager()
    dialog = EquationEditorDialog(manager)
    dialog.show()
    assert dialog.isVisible()
    assert dialog.windowTitle() == "Equation Editor"
    dialog.close()

def test_add_equation(qapp):
    manager = EquationManager()
    dialog = EquationEditorDialog(manager)
    
    initial_count = len(manager.equations)
    dialog.add_btn.click()
    
    assert len(manager.equations) == initial_count + 1
    assert dialog.table.rowCount() == initial_count + 1
    
    # Check if first row ID is eq0
    id_widget = dialog.table.cellWidget(0, 0)
    assert id_widget.text() == "eq0"
    dialog.close()

def test_delete_equation(qapp):
    manager = EquationManager()
    dialog = EquationEditorDialog(manager)
    
    dialog.add_btn.click() # eq0
    dialog.add_btn.click() # eq1
    
    # Delete eq0 (it's at row 0)
    # Find delete button in row 0, column 2
    container = dialog.table.cellWidget(0, 2)
    del_btn = container.layout().itemAt(1).widget()
    del_btn.click()
    
    assert len(manager.equations) == 1
    assert "eq0" not in manager.equations
    assert "eq1" in manager.equations
    dialog.close()
