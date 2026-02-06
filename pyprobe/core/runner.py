"""
The subprocess that executes the target script with variable tracing.
Handles command reception and data transmission to GUI.
"""

import sys
import os
import io
import threading
import traceback
from pathlib import Path
from typing import List, Optional, Set
import multiprocessing as mp

from .tracer import VariableTracer, WatchConfig, ThrottleStrategy, CapturedVariable
from .anchor import ProbeAnchor
from ..ipc.channels import IPCChannel
from ..ipc.messages import (
    Message, MessageType, make_variable_data_msg, make_exception_msg, make_probe_value_msg
)


class ScriptRunner:
    """
    Runs a target Python script in a subprocess with variable tracing.

    Lifecycle:
    1. Initialize with target script path
    2. Start execution in subprocess
    3. Receive watch list updates from GUI
    4. Send variable captures back to GUI
    5. Handle pause/resume/stop commands
    """

    def __init__(
        self,
        script_path: str,
        ipc_channel: IPCChannel,
        script_args: Optional[list] = None,
        initial_watches: Optional[List[str]] = None
    ):
        """
        Args:
            script_path: Path to the Python script to execute
            ipc_channel: IPC channel for communication with GUI
            script_args: Optional arguments to pass to the script
            initial_watches: Optional list of variable names to watch from start
        """
        self._script_path = Path(script_path).resolve()
        self._ipc = ipc_channel
        self._script_args = script_args or []
        self._initial_watches = initial_watches or []

        self._tracer: Optional[VariableTracer] = None
        self._running = False
        self._paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially

        # Command listener thread
        self._cmd_thread: Optional[threading.Thread] = None

    def run(self) -> int:
        """
        Execute the target script with tracing.

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        self._running = True

        # Create tracer with callback to send data to GUI
        # MUST happen before starting command listener to avoid race condition
        self._tracer = VariableTracer(
            data_callback=self._on_variable_captured,
            target_files={str(self._script_path)},  # Only trace the target script
            anchor_data_callback=self._on_anchor_captured
        )

        # Start command listener thread (after tracer is ready)
        self._cmd_thread = threading.Thread(target=self._command_listener, daemon=True)
        self._cmd_thread.start()

        # Add initial watches before starting
        for var_name in self._initial_watches:
            config = WatchConfig(
                var_name=var_name,
                throttle_strategy=ThrottleStrategy.TIME_BASED,
                throttle_param=50.0
            )
            self._tracer.add_watch(config)

        # Notify GUI that script is starting
        self._ipc.send_data(Message(msg_type=MessageType.DATA_SCRIPT_START))

        try:
            # Capture stdout/stderr
            old_stdout, old_stderr = sys.stdout, sys.stderr
            sys.stdout = _TeeWriter(old_stdout, self._on_stdout)
            sys.stderr = _TeeWriter(old_stderr, self._on_stderr)

            # Prepare script globals
            script_globals = {
                '__name__': '__main__',
                '__file__': str(self._script_path),
                '__builtins__': __builtins__,
            }

            # Set up sys.argv
            old_argv = sys.argv
            sys.argv = [str(self._script_path)] + self._script_args

            # Add script directory to path
            script_dir = str(self._script_path.parent)
            if script_dir not in sys.path:
                sys.path.insert(0, script_dir)

            # Start tracing (M1: use anchored tracer)
            self._tracer.start_anchored()

            # Give GUI time to send initial probe commands
            # (probes added before Run was clicked)
            import time
            deadline = time.time() + 0.1  # 100ms window
            while time.time() < deadline:
                msg = self._ipc.receive_command(timeout=0.01)
                if msg:
                    self._handle_command(msg)

            # Execute the script
            with open(self._script_path, 'r') as f:
                code = compile(f.read(), str(self._script_path), 'exec')
                exec(code, script_globals)

            return 0

        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 1

        except Exception as e:
            # Send exception to GUI
            self._send_exception(e)
            return 1

        finally:
            # Cleanup
            if self._tracer:
                self._tracer.stop()
            self._running = False
            sys.stdout, sys.stderr = old_stdout, old_stderr
            sys.argv = old_argv

            # Notify GUI that script ended
            self._ipc.send_data(Message(msg_type=MessageType.DATA_SCRIPT_END))

    def _on_variable_captured(self, captured: CapturedVariable) -> None:
        """Callback when tracer captures a variable."""
        # Check if paused
        self._pause_event.wait()

        msg = make_variable_data_msg(
            var_name=captured.name,
            value=captured.value,
            dtype=captured.dtype,
            shape=captured.shape,
            source_file=captured.source_file,
            line_number=captured.line_number,
            function_name=captured.function_name
        )
        self._ipc.send_data(msg)

    def _on_anchor_captured(self, anchor: ProbeAnchor, captured: CapturedVariable) -> None:
        """Callback when tracer captures a variable via anchor-based tracing."""
        # Check if paused
        self._pause_event.wait()

        msg = make_probe_value_msg(
            anchor=anchor,
            value=captured.value,
            dtype=captured.dtype,
            shape=captured.shape,
        )
        self._ipc.send_data(msg)

    def _command_listener(self) -> None:
        """Listen for commands from GUI in a separate thread."""
        while self._running:
            msg = self._ipc.receive_command(timeout=0.1)
            if msg is None:
                continue

            self._handle_command(msg)

    def _handle_command(self, msg: Message) -> None:
        """Process a command from the GUI."""
        if msg.msg_type == MessageType.CMD_ADD_WATCH:
            strategy_name = msg.payload.get('strategy', 'TIME_BASED').upper()
            try:
                strategy = ThrottleStrategy[strategy_name]
            except KeyError:
                strategy = ThrottleStrategy.TIME_BASED

            config = WatchConfig(
                var_name=msg.payload['var_name'],
                throttle_strategy=strategy,
                throttle_param=msg.payload.get('throttle_ms', 50.0)
            )
            self._tracer.add_watch(config)

        elif msg.msg_type == MessageType.CMD_REMOVE_WATCH:
            self._tracer.remove_watch(msg.payload['var_name'])

        elif msg.msg_type == MessageType.CMD_SET_THROTTLE:
            strategy_name = msg.payload.get('strategy', 'TIME_BASED').upper()
            try:
                strategy = ThrottleStrategy[strategy_name]
            except KeyError:
                strategy = ThrottleStrategy.TIME_BASED

            self._tracer.set_throttle(
                msg.payload['var_name'],
                strategy,
                msg.payload.get('param', 50.0)
            )

        elif msg.msg_type == MessageType.CMD_PAUSE:
            self._paused = True
            self._pause_event.clear()

        elif msg.msg_type == MessageType.CMD_RESUME:
            self._paused = False
            self._pause_event.set()

        elif msg.msg_type == MessageType.CMD_STOP:
            self._running = False
            self._pause_event.set()  # Unblock if paused
            # Force exit
            os._exit(0)

        # M1: Anchor-based handlers
        elif msg.msg_type == MessageType.CMD_ADD_PROBE:
            anchor = ProbeAnchor.from_dict(msg.payload['anchor'])
            throttle_ms = msg.payload.get('throttle_ms', 50.0)
            config = WatchConfig(
                var_name=anchor.symbol,
                throttle_strategy=ThrottleStrategy.TIME_BASED,
                throttle_param=throttle_ms,
            )
            self._tracer.add_anchor_watch(anchor, config)

        elif msg.msg_type == MessageType.CMD_REMOVE_PROBE:
            anchor = ProbeAnchor.from_dict(msg.payload['anchor'])
            self._tracer.remove_anchor_watch(anchor)

    def _on_stdout(self, text: str) -> None:
        """Send stdout to GUI."""
        self._ipc.send_data(Message(
            msg_type=MessageType.DATA_STDOUT,
            payload={'text': text}
        ))

    def _on_stderr(self, text: str) -> None:
        """Send stderr to GUI."""
        self._ipc.send_data(Message(
            msg_type=MessageType.DATA_STDERR,
            payload={'text': text}
        ))

    def _send_exception(self, exc: Exception) -> None:
        """Send exception info to GUI."""
        msg = make_exception_msg(
            exc_type=type(exc).__name__,
            message=str(exc),
            traceback=traceback.format_exc()
        )
        self._ipc.send_data(msg)


class _TeeWriter:
    """Write to both original stream and callback."""

    def __init__(self, original, callback):
        self._original = original
        self._callback = callback

    def write(self, text):
        self._original.write(text)
        if text:
            self._callback(text)

    def flush(self):
        self._original.flush()


def run_script_subprocess(
    script_path: str,
    cmd_queue: mp.Queue,
    data_queue: mp.Queue,
    initial_watches: Optional[list] = None
):
    """
    Entry point for the subprocess.
    Called via multiprocessing.Process(target=run_script_subprocess, ...)
    """
    ipc = IPCChannel(is_gui_side=False)
    # Replace queues with the ones passed from parent
    ipc._command_queue = cmd_queue
    ipc._data_queue = data_queue

    runner = ScriptRunner(script_path, ipc, initial_watches=initial_watches)
    exit_code = runner.run()

    ipc.cleanup()
    # Use os._exit() for immediate termination without waiting for threads
    os._exit(exit_code)
