"""
State Machine Tests for Button Logic

Tests all 7 transitions defined in button-state-diagrams.md:
- T1: IDLE → Click Run → EXECUTING
- T2: EXECUTING → Click Pause → PAUSED
- T3: PAUSED → Click Resume → EXECUTING  
- T4: EXECUTING → Click Stop → IDLE
- T5: PAUSED → Click Stop → IDLE
- T6: EXECUTING → Script Ends (Loop OFF) → IDLE
- T7: EXECUTING → Script Ends (Loop ON) → EXECUTING

Uses a test harness that simulates MainWindow behavior without full GUI.
"""

import sys
import os
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from pyprobe.gui.control_bar import ControlBar


class StateTestHarness:
    """
    Test harness simulating MainWindow state machine.
    
    States:
    - IDLE: _is_running=False, _is_paused=False, button="Run"
    - EXECUTING: _is_running=True, _is_paused=False, button="Pause"
    - PAUSED: _is_running=True, _is_paused=True, button="Resume"
    """
    
    def __init__(self):
        self.control_bar = ControlBar()
        self.control_bar.set_script_loaded(True, "/tmp/test.py")
        
        # Internal state (mirrors MainWindow)
        self._is_running = False
        self._is_paused = False
        self._user_stopped = False
        
        # Mock IPC and subprocess
        self.ipc = Mock()
        self.runner_process = None
        
        # Transition log for debugging
        self.transition_log = []
        
    def _log(self, event: str):
        state = self.current_state()
        self.transition_log.append(f"{event} -> {state}")
        
    def current_state(self) -> str:
        """Return current state name."""
        if not self._is_running:
            return "IDLE"
        elif self._is_paused:
            return "PAUSED"
        else:
            return "EXECUTING"
    
    # === Button Click Actions ===
    
    def click_run(self):
        """Simulate clicking Run button (T1)."""
        if self._is_running:
            raise ValueError("Cannot click Run while running")
        
        self._user_stopped = False
        self._is_running = True
        self._is_paused = False
        self.runner_process = Mock()
        self.control_bar.set_running(True)
        self._log("click_run")
        
    def click_pause(self):
        """Simulate clicking Pause button (T2)."""
        if not self._is_running or self._is_paused:
            raise ValueError("Can only pause while executing")
        
        self._is_paused = True
        self.control_bar.set_paused(True)
        self._log("click_pause")
        
    def click_resume(self):
        """Simulate clicking Resume button (T3)."""
        if not self._is_paused:
            raise ValueError("Can only resume while paused")
        
        self._is_paused = False
        self.control_bar.set_paused(False)
        self._log("click_resume")
        
    def click_stop(self):
        """Simulate clicking Stop button (T4, T5)."""
        if not self._is_running:
            raise ValueError("Cannot stop while idle")
        
        self._user_stopped = True
        self._is_running = False
        self._is_paused = False
        self.runner_process = None
        self.ipc = None
        self.control_bar.set_running(False)
        self._log("click_stop")
        
    def enable_loop(self):
        """Enable loop mode."""
        self.control_bar._loop_btn.setChecked(True)
        
    def disable_loop(self):
        """Disable loop mode."""
        self.control_bar._loop_btn.setChecked(False)
        
    def simulate_script_end(self):
        """Simulate script completion (T6, T7)."""
        should_loop = self.control_bar.is_loop_enabled and not self._user_stopped
        
        if should_loop:
            # T7: Loop restart - stay in EXECUTING
            self._soft_cleanup_for_loop()
            self._restart_loop()
            self._log("script_end_loop")
        else:
            # T6: Script ends - go to IDLE
            self._cleanup_run()
            self._log("script_end_idle")
            
    def _soft_cleanup_for_loop(self):
        """Cleanup for loop restart."""
        self._is_running = False
        self.runner_process = None
        
    def _restart_loop(self):
        """Restart for loop."""
        self.runner_process = Mock()
        self._is_running = True
        
    def _cleanup_run(self):
        """Full cleanup."""
        self._is_running = False
        self._is_paused = False
        self.runner_process = None
        self.ipc = None
        self.control_bar.set_running(False)
        
    # === Assertions ===
    
    def assert_state(self, expected: str):
        """Assert current state."""
        actual = self.current_state()
        assert actual == expected, f"Expected state {expected}, got {actual}"
        
    def assert_action_button_text(self, expected: str):
        """Assert action button text."""
        actual = self.control_bar._action_btn.text()
        assert actual == expected, f"Expected button '{expected}', got '{actual}'"
        
    def assert_stop_enabled(self, expected: bool):
        """Assert stop button enabled state."""
        actual = self.control_bar._stop_btn.isEnabled()
        assert actual == expected, f"Expected stop enabled={expected}, got {actual}"
        
    def assert_is_running(self, expected: bool):
        """Assert _is_running flag."""
        assert self._is_running == expected, f"Expected _is_running={expected}, got {self._is_running}"


# === Individual Transition Tests ===

def test_T1_idle_to_executing():
    """T1: IDLE → Click 'Run' → EXECUTING"""
    app = QApplication.instance() or QApplication(sys.argv)
    h = StateTestHarness()
    
    print("T1: IDLE → Click 'Run' → EXECUTING")
    h.assert_state("IDLE")
    h.assert_action_button_text("Run")
    
    h.click_run()
    
    h.assert_state("EXECUTING")
    h.assert_action_button_text("Pause")
    h.assert_stop_enabled(True)
    print("  ✓ PASSED")


def test_T2_executing_to_paused():
    """T2: EXECUTING → Click 'Pause' → PAUSED"""
    app = QApplication.instance() or QApplication(sys.argv)
    h = StateTestHarness()
    
    print("T2: EXECUTING → Click 'Pause' → PAUSED")
    h.click_run()
    h.assert_state("EXECUTING")
    
    h.click_pause()
    
    h.assert_state("PAUSED")
    h.assert_action_button_text("Resume")
    h.assert_stop_enabled(True)
    print("  ✓ PASSED")


def test_T3_paused_to_executing():
    """T3: PAUSED → Click 'Resume' → EXECUTING"""
    app = QApplication.instance() or QApplication(sys.argv)
    h = StateTestHarness()
    
    print("T3: PAUSED → Click 'Resume' → EXECUTING")
    h.click_run()
    h.click_pause()
    h.assert_state("PAUSED")
    
    h.click_resume()
    
    h.assert_state("EXECUTING")
    h.assert_action_button_text("Pause")
    print("  ✓ PASSED")


def test_T4_executing_to_idle_stop():
    """T4: EXECUTING → Click 'Stop' → IDLE"""
    app = QApplication.instance() or QApplication(sys.argv)
    h = StateTestHarness()
    
    print("T4: EXECUTING → Click 'Stop' → IDLE")
    h.click_run()
    h.assert_state("EXECUTING")
    
    h.click_stop()
    
    h.assert_state("IDLE")
    h.assert_action_button_text("Run")
    h.assert_stop_enabled(False)
    print("  ✓ PASSED")


def test_T5_paused_to_idle_stop():
    """T5: PAUSED → Click 'Stop' → IDLE"""
    app = QApplication.instance() or QApplication(sys.argv)
    h = StateTestHarness()
    
    print("T5: PAUSED → Click 'Stop' → IDLE")
    h.click_run()
    h.click_pause()
    h.assert_state("PAUSED")
    
    h.click_stop()
    
    h.assert_state("IDLE")
    h.assert_action_button_text("Run")
    h.assert_stop_enabled(False)
    print("  ✓ PASSED")


def test_T6_script_ends_loop_off():
    """T6: EXECUTING → Script Ends (Loop OFF) → IDLE"""
    app = QApplication.instance() or QApplication(sys.argv)
    h = StateTestHarness()
    
    print("T6: EXECUTING → Script Ends (Loop OFF) → IDLE")
    h.disable_loop()
    h.click_run()
    h.assert_state("EXECUTING")
    
    h.simulate_script_end()
    
    h.assert_state("IDLE")
    h.assert_action_button_text("Run")
    h.assert_stop_enabled(False)
    print("  ✓ PASSED")


def test_T7_script_ends_loop_on():
    """T7: EXECUTING → Script Ends (Loop ON) → EXECUTING"""
    app = QApplication.instance() or QApplication(sys.argv)
    h = StateTestHarness()
    
    print("T7: EXECUTING → Script Ends (Loop ON) → EXECUTING")
    h.enable_loop()
    h.click_run()
    h.assert_state("EXECUTING")
    
    h.simulate_script_end()
    
    h.assert_state("EXECUTING")
    h.assert_is_running(True)
    # Note: button text managed by control_bar which doesn't know about loop restart
    print("  ✓ PASSED")


def test_T7_multiple_loops():
    """T7 extended: Verify multiple loop iterations maintain EXECUTING state"""
    app = QApplication.instance() or QApplication(sys.argv)
    h = StateTestHarness()
    
    print("T7+: Multiple loop iterations stay EXECUTING")
    h.enable_loop()
    h.click_run()
    
    for i in range(10):
        h.simulate_script_end()
        h.assert_state("EXECUTING")
        h.assert_is_running(True)
    
    print(f"  ✓ PASSED (10 loops, all EXECUTING)")


def test_loop_disabled_mid_execution():
    """Loop disabled mid-execution should end at IDLE on next script end"""
    app = QApplication.instance() or QApplication(sys.argv)
    h = StateTestHarness()
    
    print("Loop disabled mid-execution → next end goes to IDLE")
    h.enable_loop()
    h.click_run()
    h.simulate_script_end()  # Loop continues
    h.assert_state("EXECUTING")
    
    h.disable_loop()
    h.simulate_script_end()  # Now should stop
    
    h.assert_state("IDLE")
    print("  ✓ PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("Button State Machine Tests")
    print("=" * 60)
    
    test_T1_idle_to_executing()
    test_T2_executing_to_paused()
    test_T3_paused_to_executing()
    test_T4_executing_to_idle_stop()
    test_T5_paused_to_idle_stop()
    test_T6_script_ends_loop_off()
    test_T7_script_ends_loop_on()
    test_T7_multiple_loops()
    test_loop_disabled_mid_execution()
    
    print("=" * 60)
    print("ALL STATE MACHINE TESTS PASSED")
    print("=" * 60)
