import pytest
from PyQt6.QtCore import Qt
from pyprobe.gui.main_window import MainWindow
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.trace_reference_manager import TraceReferenceManager

@pytest.fixture
def main_window(qtbot):
    # Reset singletons
    TraceReferenceManager._instance = None
    
    mw = MainWindow()
    qtbot.addWidget(mw)
    mw.show()
    return mw

def test_closing_last_panel_unprobes_globally(main_window, qtbot):
    # 1. Probe a variable
    anchor = ProbeAnchor(file="test.py", line=10, col=0, symbol="x")
    main_window._on_probe_requested(anchor)
    
    # Verify it's live in registry and code viewer
    assert anchor in main_window._probe_registry.active_anchors
    trace_id = main_window._probe_registry.get_trace_id(anchor)
    assert trace_id == "tr0"
    
    # 2. Get the panel and its close button
    panel = main_window._probe_container.get_all_panels()[0]
    from PyQt6.QtWidgets import QPushButton
    close_btn = None
    for child in panel.findChildren(QPushButton):
        if child.text() == "×":
            close_btn = child
            break
    
    # 3. Click close button
    qtbot.mouseClick(close_btn, Qt.MouseButton.LeftButton)
    
    # Wait for async unprobe_signal and subsequent removal
    qtbot.wait(500)
    
    # 4. Verify it's unprobed globally
    assert anchor not in main_window._probe_registry.active_anchors
    # Registry remove_probe should have been called by MainWindow via _on_unprobe_requested
