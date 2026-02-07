
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

def test_loop_state_transitions():
    """Test loop button state transitions per button-state-diagrams.md"""
    app = QApplication.instance() or QApplication(sys.argv)
    bar = ControlBar()
    
    bar.set_script_loaded(True, "/tmp/test.py")
    
    print("\nLoop State Tests:")
    
    # Test: Loop toggle in idle state
    print("  Toggle loop in idle...")
    assert not bar.is_loop_enabled
    bar._loop_btn.setChecked(True)
    assert bar.is_loop_enabled
    print("    OK: Loop enabled")
    
    # Test: Start with loop enabled - button should show Pause
    print("  Start running with loop enabled...")
    bar.set_running(True)
    assert bar._action_btn.text() == "Pause"
    assert bar.is_loop_enabled  # Loop stays enabled
    print("    OK: Action=Pause, Loop stays enabled")
    
    # Test: set_running(False) resets action button but loop stays enabled
    print("  Stop running (set_running False)...")
    bar.set_running(False)
    assert bar._action_btn.text() == "Run"
    assert bar.is_loop_enabled  # Loop should STAY enabled
    print("    OK: Action=Run, Loop STILL enabled")
    
    # Test: Loop toggle during run should work
    print("  Loop toggle during execution...")
    bar.set_running(True)
    bar._loop_btn.setChecked(False)
    assert not bar.is_loop_enabled
    bar._loop_btn.setChecked(True)
    assert bar.is_loop_enabled
    print("    OK: Loop toggle works during run")
    
    # Test: Pause state
    print("  Pause state with loop...")
    bar.set_paused(True)
    assert bar._action_btn.text() == "Resume"
    assert bar.is_loop_enabled  # Loop unaffected by pause
    print("    OK: Action=Resume, Loop unaffected")
    
    bar.set_paused(False)
    bar.set_running(False)
    
    print("\nLoop state tests passed!")

if __name__ == "__main__":
    test_control_bar_logic()
    test_loop_state_transitions()
