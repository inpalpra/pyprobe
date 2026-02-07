
import sys
from PyQt6.QtWidgets import QApplication
from pyprobe.gui.control_bar import ControlBar

def test_control_bar_logic():
    app = QApplication(sys.argv)
    bar = ControlBar()
    
    print("Initial State:")
    print(f"  Script Loaded: {bar._script_loaded}")
    print(f"  Running: {bar._is_running}")
    print(f"  Paused: {bar._is_paused}")
    print(f"  Action Text: {bar._action_btn.text()}")
    print(f"  Loop Enabled: {bar.is_loop_enabled}")
    
    assert bar._action_btn.text() == "Run"
    assert not bar._action_btn.isEnabled()
    
    print("\nLoad Script:")
    bar.set_script_loaded(True, "/tmp/test.py")
    print(f"  Action Text: {bar._action_btn.text()}")
    assert bar._action_btn.isEnabled()
    assert bar._action_btn.text() == "Run"
    
    print("\nStart Running:")
    bar.set_running(True)
    print(f"  Action Text: {bar._action_btn.text()}")
    assert bar._action_btn.text() == "Pause"
    assert bar._stop_btn.isEnabled()
    
    print("\nPause:")
    bar.set_paused(True)
    print(f"  Action Text: {bar._action_btn.text()}")
    assert bar._action_btn.text() == "Resume"
    
    print("\nResume:")
    bar.set_paused(False)
    print(f"  Action Text: {bar._action_btn.text()}")
    assert bar._action_btn.text() == "Pause"
    
    print("\nStop:")
    bar.set_running(False)
    print(f"  Action Text: {bar._action_btn.text()}")
    assert bar._action_btn.text() == "Run"
    
    print("\nExiting test successfully.")

if __name__ == "__main__":
    test_control_bar_logic()
