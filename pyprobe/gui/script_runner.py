"""
Script execution lifecycle management.

Extracted from MainWindow to separate concerns.
Handles: start, stop, pause, resume, loop restart, cleanup.
"""

from typing import Optional, List, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import multiprocessing as mp

from pyprobe.logging import get_logger, trace_print
logger = get_logger(__name__)

from ..ipc.channels import IPCChannel
from ..ipc.messages import Message, MessageType, make_add_probe_cmd
from ..core.runner import run_script_subprocess
from ..core.anchor import ProbeAnchor


class ScriptRunner(QObject):
    """
    Manages script execution lifecycle.
    
    Signals:
        started: Emitted when script starts running
        ended: Emitted when script ends (naturally or stopped)
        paused: Emitted when script is paused
        resumed: Emitted when script is resumed
        loop_restarted: Emitted when loop mode restarts (with loop count)
    """
    
    started = pyqtSignal()
    ended = pyqtSignal()
    paused = pyqtSignal()
    resumed = pyqtSignal()
    loop_restarted = pyqtSignal(int)  # loop count
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self._script_path: Optional[str] = None
        self._runner_process: Optional[mp.Process] = None
        self._ipc: Optional[IPCChannel] = None
        self._is_running = False
        self._is_paused = False
        self._user_stopped = False
        self._loop_count = 0
        
        # Callbacks to get state from MainWindow
        self._get_active_anchors: Optional[Callable[[], List[ProbeAnchor]]] = None
        self._tracer = None
    
    def configure(
        self,
        script_path: str,
        get_active_anchors: Callable[[], List[ProbeAnchor]],
        tracer = None
    ):
        """Configure the runner with script path and anchor accessor."""
        self._script_path = script_path
        self._get_active_anchors = get_active_anchors
        self._tracer = tracer
    
    @property
    def is_running(self) -> bool:
        return self._is_running
    
    @property
    def is_paused(self) -> bool:
        return self._is_paused
    
    @property
    def ipc(self) -> Optional[IPCChannel]:
        """Access to IPC channel for message polling."""
        return self._ipc
    
    @property
    def loop_count(self) -> int:
        return self._loop_count
    
    def start(self) -> bool:
        """
        Start running the configured script.
        
        Returns:
            True if started successfully, False otherwise.
        """
        if not self._script_path:
            return False
        
        if self._tracer:
            self._tracer.trace_action_run_clicked()
        
        self._user_stopped = False
        self._loop_count = 0
        
        # Create IPC channel
        self._ipc = IPCChannel(is_gui_side=True)
        
        # Start runner subprocess
        self._runner_process = mp.Process(
            target=run_script_subprocess,
            args=(
                self._script_path,
                self._ipc.command_queue,
                self._ipc.data_queue,
                []  # No legacy watches
            )
        )
        self._runner_process.start()
        
        # Send probe commands for existing anchors
        if self._get_active_anchors:
            anchors = list(self._get_active_anchors())
            trace_print(f"ScriptRunner.start: Sending ADD_PROBE for {len(anchors)} anchors")
            for anchor in anchors:
                trace_print(f"ScriptRunner.start: ADD_PROBE {anchor.symbol} at line {anchor.line}")
                msg = make_add_probe_cmd(anchor)
                self._ipc.send_command(msg)
        
        # Send START command to begin execution
        self._ipc.send_command(Message(msg_type=MessageType.CMD_START))
        

        
        self._is_running = True
        self._is_paused = False
        
        if self._tracer:
            self._tracer.trace_reaction_subprocess_started(self._runner_process.pid)
            self._tracer.trace_reaction_state_changed("run started")
        
        self.started.emit()
        return True
    
    def stop(self):
        """Stop script execution."""
        if self._tracer:
            self._tracer.trace_action_stop_clicked()
        
        self._user_stopped = True
        
        if self._ipc and self._is_running:
            self._ipc.send_command(Message(msg_type=MessageType.CMD_STOP))
            if self._tracer:
                self._tracer.trace_ipc_sent("CMD_STOP")
        
        if self._runner_process:
            self._runner_process.join(timeout=2.0)
            if self._runner_process.is_alive():
                self._runner_process.terminate()
        
        self.cleanup()
    
    def toggle_pause(self) -> bool:
        """
        Toggle pause/resume state.
        
        Returns:
            True if now paused, False if now running.
        """
        if not self._ipc:
            return self._is_paused
        
        if not self._is_paused:
            # Pause
            if self._tracer:
                self._tracer.trace_action_pause_clicked()
            self._ipc.send_command(Message(msg_type=MessageType.CMD_PAUSE))
            if self._tracer:
                self._tracer.trace_ipc_sent("CMD_PAUSE")
            self._is_paused = True
            if self._tracer:
                self._tracer.trace_reaction_state_changed("paused")
            self.paused.emit()
        else:
            # Resume
            if self._tracer:
                self._tracer.trace_action_resume_clicked()
            self._ipc.send_command(Message(msg_type=MessageType.CMD_RESUME))
            if self._tracer:
                self._tracer.trace_ipc_sent("CMD_RESUME")
            self._is_paused = False
            if self._tracer:
                self._tracer.trace_reaction_state_changed("resumed")
            self.resumed.emit()
        
        return self._is_paused
    
    def restart_loop(self) -> bool:
        """
        Restart script for loop mode with existing IPC.
        
        Returns:
            True if restart succeeded, False otherwise.
        """
        logger.debug("ScriptRunner.restart_loop called")
        
        if not self._script_path or not self._ipc:
            logger.debug(f"  ABORT: script_path={self._script_path}, ipc={self._ipc}")
            self.cleanup()
            return False
        
        logger.debug(f"  starting new subprocess for {self._script_path}")
        
        # Start new subprocess with existing IPC queues
        self._runner_process = mp.Process(
            target=run_script_subprocess,
            args=(
                self._script_path,
                self._ipc.command_queue,
                self._ipc.data_queue,
                []
            )
        )
        self._runner_process.start()
        logger.debug(f"  new process pid={self._runner_process.pid}")
        
        self._loop_count += 1
        
        if self._tracer:
            self._tracer.trace_loop_restart(self._loop_count)
            self._tracer.trace_reaction_subprocess_started(self._runner_process.pid)
        
        # Re-send probe commands for the new subprocess
        if self._get_active_anchors:
            for anchor in self._get_active_anchors():
                msg = make_add_probe_cmd(anchor)
                self._ipc.send_command(msg)
        
        # Send START command to begin execution
        self._ipc.send_command(Message(msg_type=MessageType.CMD_START))
        
        self._is_running = True
        self._is_paused = False
        
        logger.debug(f"  loop restart complete, _is_running={self._is_running}")
        
        self.loop_restarted.emit(self._loop_count)
        return True
    
    def soft_cleanup_for_loop(self):
        """Clean up subprocess for loop restart without closing IPC."""
        logger.debug("ScriptRunner.soft_cleanup_for_loop called")
        
        if self._tracer:
            self._tracer.trace_reaction_cleanup("soft cleanup for loop")
        
        self._is_running = False
        
        # Terminate subprocess only, keep IPC open
        proc = self._runner_process
        if proc is not None:
            logger.debug(f"  waiting for process (pid={proc.pid})")
            proc.join(timeout=0.5)
            if proc.is_alive():
                logger.debug("  process still alive, terminating")
                proc.terminate()
                proc.join(timeout=0.5)
            logger.debug(f"  process exit code: {proc.exitcode}")
            if self._tracer:
                self._tracer.trace_reaction_subprocess_ended(proc.exitcode)
        
        self._runner_process = None
        logger.debug(f"  IPC still valid: {self._ipc is not None}")
    
    def cleanup(self):
        """Full cleanup after script run."""
        if self._tracer:
            self._tracer.trace_reaction_cleanup("full cleanup started")
        
        self._is_running = False
        self._is_paused = False
        
        # Terminate subprocess
        proc = self._runner_process
        if proc is not None:
            proc.join(timeout=0.5)
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=0.5)
                if proc.is_alive():
                    proc.kill()
                    proc.join(timeout=0.1)
            if self._tracer:
                self._tracer.trace_reaction_subprocess_ended(proc.exitcode)
        
        # Clean up IPC
        if self._ipc is not None:
            self._ipc.cleanup()
        
        self._ipc = None
        self._runner_process = None
        
        if self._tracer:
            self._tracer.trace_reaction_state_changed("cleanup complete, now IDLE")
        
        self.ended.emit()
    
    @property
    def user_stopped(self) -> bool:
        """Whether user manually stopped (prevents auto loop)."""
        return self._user_stopped
