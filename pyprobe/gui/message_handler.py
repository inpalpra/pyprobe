"""
IPC message handler for polling and dispatching messages from the script runner.

Extracted from MainWindow to separate concerns.
Handles: polling IPC queue, dispatching by message type, emitting Qt signals.
"""

from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from pyprobe.logging import get_logger, trace_print
logger = get_logger(__name__)

from ..ipc.messages import Message, MessageType
from ..core.anchor import ProbeAnchor


class MessageHandler(QObject):
    """
    Handles IPC message polling and dispatch.
    
    Signals:
        probe_value: Emitted when probe data arrives (anchor_dict, payload)
        probe_value_batch: Emitted when batched probe data arrives (list of probe_data)
        script_ended: Emitted when script execution completes
        exception_raised: Emitted when script raises exception (payload dict)
        variable_data: Emitted for legacy variable data (payload dict)
    """
    
    # Signals for thread-safe GUI updates
    probe_value = pyqtSignal(dict)  # Full payload with anchor, value, dtype
    probe_value_batch = pyqtSignal(list)  # List of probe payloads
    script_ended = pyqtSignal()
    exception_raised = pyqtSignal(dict)
    variable_data = pyqtSignal(dict)  # Legacy support
    
    def __init__(self, script_runner, tracer=None, parent: Optional[QObject] = None):
        """
        Initialize MessageHandler.
        
        Args:
            script_runner: ScriptRunner instance to get IPC channel and process state
            tracer: State tracer for debugging (optional)
            parent: Parent QObject
        """
        super().__init__(parent)
        self._script_runner = script_runner
        self._tracer = tracer
        self._frame_count = 0
        
        # Polling timer
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll)
        
    @property
    def frame_count(self) -> int:
        """Number of data frames received since last reset."""
        return self._frame_count
    
    def reset_frame_count(self) -> int:
        """Reset frame count and return previous value."""
        count = self._frame_count
        self._frame_count = 0
        return count
        
    def start_polling(self, interval_ms: int = 16):
        """
        Start polling the IPC queue.
        
        Args:
            interval_ms: Poll interval in milliseconds (default 16 = ~60fps)
        """
        self._poll_timer.setInterval(interval_ms)
        self._poll_timer.start()
        logger.debug(f"Started IPC polling at {interval_ms}ms interval")
        
    def stop_polling(self):
        """Stop polling the IPC queue."""
        self._poll_timer.stop()
        logger.debug("Stopped IPC polling")
        
    def _poll(self):
        """Poll the IPC queue for incoming data."""
        # Fast exit if not running
        if not self._script_runner.is_running:
            return

        ipc = self._script_runner.ipc
        if ipc is None:
            return

        # Check subprocess status - critical for debugging
        proc = self._script_runner._runner_process
        subprocess_alive = proc is not None and proc.is_alive() if proc else False
        
        # Process available messages without blocking (timeout=0 is non-blocking)
        # Limit to 50 messages per frame to keep GUI responsive
        messages_this_poll = 0
        for _ in range(50):
            if not self._script_runner.is_running:
                break

            try:
                msg = ipc.receive_data(timeout=0)
            except (AttributeError, OSError, EOFError, BrokenPipeError) as e:
                # IPC was cleaned up or queue closed
                if self._tracer:
                    self._tracer.trace_error(f"IPC receive error: {type(e).__name__}: {e}")
                break

            if msg is None:
                break

            messages_this_poll += 1
            # Log EVERY message type received
            if self._tracer:
                self._tracer.trace_ipc_received(
                    msg.msg_type.name, 
                    {"subprocess_alive": subprocess_alive, "msg_num": messages_this_poll}
                )
            self._dispatch(msg)
        
        # If subprocess died but we didn't get DATA_SCRIPT_END, that's a bug!
        # But only fire this once by checking is_running
        if not subprocess_alive and proc is not None and self._script_runner.is_running:
            exit_code = proc.exitcode
            if exit_code is not None:
                if self._tracer:
                    self._tracer.trace_error(f"Subprocess exited (code={exit_code}) but no DATA_SCRIPT_END received!")
                # Prevent repeated firing - use cleanup which sets is_running to False
                self._script_runner.soft_cleanup_for_loop()
                # Force script_ended if subprocess died
                self.script_ended.emit()

    def _dispatch(self, msg: Message):
        """
        Dispatch an incoming message by type.
        
        Args:
            msg: Message received from IPC
        """
        if msg.msg_type == MessageType.DATA_VARIABLE:
            self._frame_count += 1
            self.variable_data.emit(msg.payload)

        # Handle anchor-based probe data
        elif msg.msg_type == MessageType.DATA_PROBE_VALUE:
            self._frame_count += 1
            self.probe_value.emit(msg.payload)

        # Handle batched probe data for atomic updates
        elif msg.msg_type == MessageType.DATA_PROBE_VALUE_BATCH:
            self._frame_count += 1
            probes = msg.payload.get('probes', [])
            self.probe_value_batch.emit(probes)

        elif msg.msg_type == MessageType.DATA_SCRIPT_END:
            logger.debug("DATA_SCRIPT_END received, emitting script_ended signal")
            if self._tracer:
                proc = self._script_runner._runner_process
                self._tracer.trace_ipc_received(
                    "DATA_SCRIPT_END", 
                    {"subprocess_alive": proc.is_alive() if proc else False}
                )
            self.script_ended.emit()

        elif msg.msg_type == MessageType.DATA_EXCEPTION:
            self.exception_raised.emit(msg.payload)

        elif msg.msg_type == MessageType.DATA_STDOUT:
            pass  # Could display in a console widget

        elif msg.msg_type == MessageType.DATA_STDERR:
            pass  # Could display in a console widget
