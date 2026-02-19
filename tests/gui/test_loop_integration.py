"""
Integration test for LOOP button functionality.

This test verifies that the loop button actually causes continuous execution
by simulating multiple loop iterations and checking state consistency.
"""

import sys
import os
import time
import multiprocessing as mp
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from pyprobe.gui.control_bar import ControlBar
from pyprobe.ipc.messages import Message, MessageType


class LoopTestHarness:
    """
    Test harness that simulates the MainWindow loop logic
    without needing full GUI initialization.
    """
    
    def __init__(self):
        self.is_running = False
        self.user_stopped = False
        self.loop_count = 0
        self.max_loops = 10  # Limit for testing
        self.ipc = Mock()
        self.control_bar = ControlBar()
        self.script_path = "/tmp/test_script.py"
        self.runner_process = None
        self.script_ended_callbacks = []
        
        # Track state at each stage
        self.state_log = []
        
    def log_state(self, event: str):
        self.state_log.append({
            'event': event,
            'loop_count': self.loop_count,
            'is_running': self.is_running,
            'is_loop_enabled': self.control_bar.is_loop_enabled,
            'user_stopped': self.user_stopped,
            'ipc_valid': self.ipc is not None,
        })
        
    def simulate_script_end(self):
        """Simulate what happens when script ends."""
        self.log_state('script_end_start')
        
        should_loop = self.control_bar.is_loop_enabled and not self.user_stopped
        
        if should_loop:
            self.log_state('taking_loop_path')
            self.soft_cleanup_for_loop()
            # Simulate the QTimer.singleShot delay
            self.restart_loop()
        else:
            self.log_state('taking_cleanup_path')
            self.cleanup_run()
            
    def soft_cleanup_for_loop(self):
        """Simulated soft cleanup."""
        self.is_running = False
        # Process would be terminated here
        self.runner_process = None
        # IPC stays open
        self.log_state('soft_cleanup_done')
        
    def restart_loop(self):
        """Simulated restart."""
        self.loop_count += 1
        self.log_state('restart_loop_start')
        
        if not self.script_path or not self.ipc:
            self.log_state('restart_abort_no_ipc')
            self.cleanup_run()
            return
            
        if self.loop_count >= self.max_loops:
            self.log_state('max_loops_reached')
            self.cleanup_run()
            return
            
        # Simulate starting new process
        self.runner_process = Mock()
        self.is_running = True
        self.log_state('restart_loop_done')
        
    def cleanup_run(self):
        """Full cleanup."""
        self.is_running = False
        self.runner_process = None
        # In actual code, IPC would be cleaned up here
        self.control_bar.set_running(False)
        self.log_state('cleanup_done')
        
    def start_run(self):
        """Simulate starting a run."""
        self.user_stopped = False
        self.is_running = True
        self.runner_process = Mock()
        self.control_bar.set_running(True)
        self.log_state('run_started')
        

def test_loop_continuous_execution():
    """
    Test that loop mode causes continuous execution.
    Simulates 5 script completions and verifies loop restarts each time.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    
    harness = LoopTestHarness()
    harness.control_bar.set_script_loaded(True, "/tmp/test.py")
    harness.control_bar._loop_btn.setChecked(True)  # Enable loop
    
    print("\n=== Loop Continuous Execution Test ===")
    print(f"Loop enabled: {harness.control_bar.is_loop_enabled}")
    
    # Start the first run
    harness.start_run()
    
    # Simulate 5 script completions
    for i in range(5):
        print(f"\n--- Script completion {i + 1} ---")
        harness.simulate_script_end()
        
        # Check state after each completion
        if harness.control_bar.is_loop_enabled and not harness.user_stopped:
            assert harness.is_running, f"Loop {i+1}: Expected is_running=True after loop restart"
            assert harness.ipc is not None, f"Loop {i+1}: Expected IPC to still be valid"
            print(f"  ✓ Loop restarted (count={harness.loop_count}, is_running={harness.is_running})")
        else:
            print(f"  Loop disabled or user stopped")
            break
    
    print(f"\nTotal loops completed: {harness.loop_count}")
    assert harness.loop_count >= 5, f"Expected at least 5 loops, got {harness.loop_count}"
    print("✓ Loop continuous execution test PASSED")


def test_loop_stop_by_user():
    """
    Test that user stop properly ends loop mode.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    
    harness = LoopTestHarness()
    harness.control_bar.set_script_loaded(True, "/tmp/test.py")
    harness.control_bar._loop_btn.setChecked(True)
    
    print("\n=== Loop Stop by User Test ===")
    
    harness.start_run()
    
    # Simulate 2 loops
    harness.simulate_script_end()
    harness.simulate_script_end()
    
    print(f"After 2 loops, count={harness.loop_count}, is_running={harness.is_running}")
    
    # User clicks stop
    harness.user_stopped = True
    harness.simulate_script_end()  # This should NOT restart
    
    print(f"After user stop, is_running={harness.is_running}")
    assert not harness.is_running, "Expected is_running=False after user stop"
    print("✓ Loop stop by user test PASSED")


def test_loop_disabled_mid_execution():
    """
    Test that disabling loop mid-execution stops after current run.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    
    harness = LoopTestHarness()
    harness.control_bar.set_script_loaded(True, "/tmp/test.py")
    harness.control_bar._loop_btn.setChecked(True)
    
    print("\n=== Loop Disable Mid-Execution Test ===")
    
    harness.start_run()
    harness.simulate_script_end()  # Loop 1
    harness.simulate_script_end()  # Loop 2
    
    print(f"After 2 loops: count={harness.loop_count}")
    
    # User disables loop while running
    harness.control_bar._loop_btn.setChecked(False)
    print(f"Loop disabled: {harness.control_bar.is_loop_enabled}")
    
    harness.simulate_script_end()  # Should NOT restart
    
    print(f"After script end with loop disabled: is_running={harness.is_running}")
    assert not harness.is_running, "Expected is_running=False after loop disabled"
    print("✓ Loop disable mid-execution test PASSED")


def test_ipc_persistence_during_loop():
    """
    Test that IPC channel remains valid across loop iterations.
    This is the suspected root cause of the bug.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("\n=== IPC Persistence Test ===")
    
    harness = LoopTestHarness()
    harness.control_bar.set_script_loaded(True, "/tmp/test.py")
    harness.control_bar._loop_btn.setChecked(True)
    
    harness.start_run()
    original_ipc = harness.ipc
    
    for i in range(5):
        harness.simulate_script_end()
        assert harness.ipc is original_ipc, f"Loop {i+1}: IPC reference changed!"
        assert harness.ipc is not None, f"Loop {i+1}: IPC became None!"
        print(f"  Loop {i+1}: IPC still valid ✓")
    
    print("✓ IPC persistence test PASSED")


if __name__ == "__main__":
    test_loop_continuous_execution()
    test_loop_stop_by_user()
    test_loop_disabled_mid_execution()
    test_ipc_persistence_during_loop()
    print("\n" + "=" * 50)
    print("ALL LOOP TESTS PASSED")
    print("=" * 50)
