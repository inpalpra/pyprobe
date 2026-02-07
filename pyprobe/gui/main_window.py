"""
Main application window with probe panels and controls.

M1: Source-anchored probing with code viewer.
"""

from typing import Dict, List, Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QStatusBar, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor
import multiprocessing as mp
import os

from pyprobe.logging import get_logger
logger = get_logger(__name__)

from .probe_panel import ProbePanelContainer, ProbePanel
from .control_bar import ControlBar
from .theme.cyberpunk import apply_cyberpunk_theme
from ..ipc.channels import IPCChannel
from ..ipc.messages import Message, MessageType, make_add_probe_cmd, make_remove_probe_cmd
from ..core.runner import run_script_subprocess

# === M1 IMPORTS ===
from ..core.anchor import ProbeAnchor
from .code_viewer import CodeViewer
from .code_gutter import CodeGutter
from .code_highlighter import PythonHighlighter
from .file_watcher import FileWatcher
from .probe_registry import ProbeRegistry
from .probe_state import ProbeState
from ..analysis.anchor_mapper import AnchorMapper
from .animations import ProbeAnimations
from ..state_tracer import get_tracer


class MainWindow(QMainWindow):
    """
    Main PyProbe window.

    Layout:
    ┌────────────────────────────────────────────────────────┐
    │  [Control Bar: Open | Run | Pause | Stop]              │
    ├─────────────────┬──────────────────────────────────────┤
    │   Watch List    │        Probe Panels                  │
    │   (Variables)   │   ┌──────────┐  ┌──────────┐        │
    │                 │   │ signal_i │  │ symbols  │        │
    │   [+] signal_i  │   │ Waveform │  │ Constel. │        │
    │   [+] symbols   │   └──────────┘  └──────────┘        │
    ├─────────────────┴──────────────────────────────────────┤
    │  Status: Running dsp_demo.py | Line 42 | 60 FPS       │
    └────────────────────────────────────────────────────────┘
    """

    # Signals for thread-safe GUI updates
    variable_received = pyqtSignal(dict)
    script_ended = pyqtSignal()
    exception_occurred = pyqtSignal(dict)

    def __init__(self, script_path: Optional[str] = None, watch_variables: Optional[List[str]] = None):
        super().__init__()

        self._script_path: Optional[str] = script_path
        self._runner_process: Optional[mp.Process] = None
        self._ipc: Optional[IPCChannel] = None
        self._is_running = False  # Flag to track if script is running
        self._user_stopped = False # Flag to track if user manually stopped (prevents loop)

        # M1: Probe panels by anchor (not by variable name)
        self._probe_panels: Dict[ProbeAnchor, ProbePanel] = {}

        # FPS tracking
        self._frame_count = 0
        self._fps = 0.0

        # M1: Source file content cache for anchor mapping
        self._last_source_content: Optional[str] = None
        
        # M2: Probe metadata tracking (including lens choice)
        self._probe_metadata: Dict[ProbeAnchor, dict] = {}

        self._setup_ui()
        self._setup_signals()
        self._setup_polling_timer()

        # Apply cyberpunk theme
        apply_cyberpunk_theme(self)
        
        # Initialize state tracer
        self._tracer = get_tracer()
        self._tracer.set_main_window(self)
        self._loop_count = 0  # Track loop iterations for tracing

        # Load script if provided
        if script_path:
            self._load_script(script_path)

    def _setup_ui(self):
        """Create the UI layout."""
        self.setWindowTitle("PyProbe - Variable Probe")
        self.setMinimumSize(1200, 800)

        # Central widget with splitter
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # === M1: Code viewer with gutter (replaces watch list) ===
        code_container = QWidget()
        code_layout = QHBoxLayout(code_container)
        code_layout.setContentsMargins(0, 0, 0, 0)
        code_layout.setSpacing(0)

        self._code_viewer = CodeViewer()
        self._code_gutter = CodeGutter(self._code_viewer)
        self._highlighter = PythonHighlighter(self._code_viewer.document())

        code_layout.addWidget(self._code_gutter)
        code_layout.addWidget(self._code_viewer)
        splitter.addWidget(code_container)

        # Probe panel container (right panel)
        self._probe_container = ProbePanelContainer()
        splitter.addWidget(self._probe_container)

        splitter.setSizes([400, 800])

        # === M1: File watcher and probe registry ===
        self._file_watcher = FileWatcher(self)
        self._probe_registry = ProbeRegistry(self)

        # Control bar (toolbar)
        self._control_bar = ControlBar()
        self.addToolBar(self._control_bar)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready - Open a Python script to begin")

    def _setup_signals(self):
        """Connect signals and slots."""
        # Control bar signals
        # Control bar signals
        self._control_bar.open_clicked.connect(self._on_open_script)
        self._control_bar.action_clicked.connect(self._on_action_clicked)
        # self._control_bar.pause_clicked.connect(self._on_pause_script) # Removed
        self._control_bar.stop_clicked.connect(self._on_stop_script)

        # === M1: Code viewer signals ===
        self._code_viewer.probe_requested.connect(self._on_probe_requested)
        self._code_viewer.probe_removed.connect(self._on_probe_remove_requested)

        # === M1: File watcher signals ===
        self._file_watcher.file_changed.connect(self._on_file_changed)

        # === M1: Probe registry signals ===
        self._probe_registry.probe_state_changed.connect(self._on_probe_state_changed)

        # Internal signals (for thread-safe GUI updates)
        self.variable_received.connect(self._on_variable_data)
        self.script_ended.connect(self._on_script_ended)
        self.exception_occurred.connect(self._on_exception)

    def _setup_polling_timer(self):
        """Set up timer to poll IPC queue."""
        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self._poll_ipc)
        self._poll_timer.setInterval(16)  # ~60 FPS

        # FPS counter timer
        self._fps_timer = QTimer()
        self._fps_timer.timeout.connect(self._update_fps)
        self._fps_timer.setInterval(1000)  # Every second

    def _poll_ipc(self):
        """Poll the IPC queue for incoming data."""
        # Fast exit if not running
        if not self._is_running:
            return

        ipc = self._ipc
        if ipc is None:
            return

        # Check subprocess status - critical for debugging
        proc = self._runner_process
        subprocess_alive = proc is not None and proc.is_alive() if proc else False
        
        # Process available messages without blocking (timeout=0 is non-blocking)
        # Limit to 50 messages per frame to keep GUI responsive
        messages_this_poll = 0
        for _ in range(50):
            if not self._is_running:
                break

            try:
                msg = ipc.receive_data(timeout=0)
            except (AttributeError, OSError, EOFError, BrokenPipeError) as e:
                # IPC was cleaned up or queue closed
                self._tracer.trace_error(f"IPC receive error: {type(e).__name__}: {e}")
                break

            if msg is None:
                break

            messages_this_poll += 1
            # Log EVERY message type received
            self._tracer.trace_ipc_received(
                msg.msg_type.name, 
                {"subprocess_alive": subprocess_alive, "msg_num": messages_this_poll}
            )
            self._handle_message(msg)
        
        # If subprocess died but we didn't get DATA_SCRIPT_END, that's a bug!
        # But only fire this once by checking _is_running
        if not subprocess_alive and proc is not None and self._is_running:
            exit_code = proc.exitcode
            if exit_code is not None:
                self._tracer.trace_error(f"Subprocess exited (code={exit_code}) but no DATA_SCRIPT_END received!")
                # Prevent repeated firing
                self._is_running = False
                # Force script_ended if subprocess died
                self.script_ended.emit()

    def _handle_message(self, msg: Message):
        """Handle an incoming message from the runner."""
        if msg.msg_type == MessageType.DATA_VARIABLE:
            self._frame_count += 1
            # Emit signal for thread-safe GUI update
            self.variable_received.emit(msg.payload)

        # === M1: Handle anchor-based probe data ===
        elif msg.msg_type == MessageType.DATA_PROBE_VALUE:
            self._frame_count += 1
            anchor = ProbeAnchor.from_dict(msg.payload['anchor'])
            self._probe_registry.update_data_received(anchor)
            if anchor in self._probe_panels:
                # Update metadata dtype
                if anchor in self._probe_metadata:
                    self._probe_metadata[anchor]['dtype'] = msg.payload['dtype']
                
                self._probe_panels[anchor].update_data(
                    value=msg.payload['value'],
                    dtype=msg.payload['dtype'],
                    shape=msg.payload.get('shape'),
                )

        # === M1: Handle batched probe data for atomic updates ===
        elif msg.msg_type == MessageType.DATA_PROBE_VALUE_BATCH:
            self._frame_count += 1
            # Process all probes from this batch atomically
            for probe_data in msg.payload.get('probes', []):
                anchor = ProbeAnchor.from_dict(probe_data['anchor'])
                self._probe_registry.update_data_received(anchor)
                if anchor in self._probe_panels:
                    self._probe_panels[anchor].update_data(
                        value=probe_data['value'],
                        dtype=probe_data['dtype'],
                        shape=probe_data.get('shape'),
                    )

        elif msg.msg_type == MessageType.DATA_SCRIPT_END:
            # NOTE: Don't reset state here! Let _on_script_ended() handle it
            # so loop logic can properly manage restarts
            logger.debug("DATA_SCRIPT_END received, emitting script_ended signal")
            self._tracer.trace_ipc_received("DATA_SCRIPT_END", {"subprocess_alive": self._runner_process.is_alive() if self._runner_process else False})
            self.script_ended.emit()

        elif msg.msg_type == MessageType.DATA_EXCEPTION:
            self.exception_occurred.emit(msg.payload)

        elif msg.msg_type == MessageType.DATA_STDOUT:
            pass  # Could display in a console widget

        elif msg.msg_type == MessageType.DATA_STDERR:
            pass  # Could display in a console widget

    def _update_fps(self):
        """Update FPS display."""
        self._fps = self._frame_count
        self._frame_count = 0

        if self._ipc:
            self._status_bar.showMessage(
                f"Running: {os.path.basename(self._script_path or '')} | "
                f"{self._fps} updates/sec"
            )

    @pyqtSlot(dict)
    def _on_variable_data(self, payload: dict):
        """Handle variable data update (runs in GUI thread)."""
        var_name = payload['var_name']

        # Create probe panel if it doesn't exist
        if var_name not in self._probe_panels:
            panel = self._probe_container.create_panel(
                var_name=var_name,
                dtype=payload['dtype']
            )
            self._probe_panels[var_name] = panel

        # Update the panel with new data
        self._probe_panels[var_name].update_data(
            value=payload['value'],
            dtype=payload['dtype'],
            shape=payload.get('shape'),
            source_info=f"{payload['function_name']}:{payload['line_number']}"
        )

    @pyqtSlot()
    def _on_open_script(self):
        """Open file dialog to select a Python script."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Python Script",
            "",
            "Python Files (*.py);;All Files (*)"
        )
        if path:
            self._load_script(path)

    def _load_script(self, path: str):
        """Load a script file."""
        self._script_path = path
        self._status_bar.showMessage(f"Loaded: {path}")
        self._control_bar.set_script_loaded(True, path)

        # === M1: Load into code viewer and start watching ===
        self._code_viewer.load_file(path)
        self._file_watcher.watch_file(path)
        self._last_source_content = self._code_viewer.toPlainText()

    @pyqtSlot()
    def _on_action_clicked(self):
        """Handle Run/Pause/Resume action."""
        if not self._is_running:
             self._on_run_script()
        else:
             self._on_pause_script()

    @pyqtSlot()
    def _on_run_script(self):
        """Start running the loaded script."""
        if not self._script_path:
            return
        
        self._tracer.trace_action_run_clicked()

        self._user_stopped = False
        self._loop_count = 0

        # Create IPC channel
        self._ipc = IPCChannel(is_gui_side=True)

        # M1: Start with anchored mode - send existing probe anchors
        initial_watches = []  # No legacy watches in M1

        # Start runner subprocess
        self._runner_process = mp.Process(
            target=run_script_subprocess,
            args=(
                self._script_path,
                self._ipc.command_queue,
                self._ipc.data_queue,
                initial_watches
            )
        )
        self._runner_process.start()

        # M1: Send probe commands for any existing anchors
        for anchor in self._probe_registry.active_anchors:
            msg = make_add_probe_cmd(anchor)
            self._ipc.send_command(msg)

        # Mark as running and start polling
        self._is_running = True
        self._poll_timer.start()
        self._fps_timer.start()

        self._status_bar.showMessage(f"Running: {self._script_path}")
        self._control_bar.set_running(True)
        self._tracer.trace_reaction_subprocess_started(self._runner_process.pid)
        self._tracer.trace_reaction_state_changed("run started")

    @pyqtSlot()
    def _on_pause_script(self):
        """Pause/resume script execution."""
        if self._ipc:
            if not self._control_bar.is_paused:
                self._tracer.trace_action_pause_clicked()
                self._ipc.send_command(Message(msg_type=MessageType.CMD_PAUSE))
                self._tracer.trace_ipc_sent("CMD_PAUSE")
                self._control_bar.set_paused(True)
                self._status_bar.showMessage("Paused")
                self._tracer.trace_reaction_state_changed("paused")
            else:
                self._tracer.trace_action_resume_clicked()
                self._ipc.send_command(Message(msg_type=MessageType.CMD_RESUME))
                self._tracer.trace_ipc_sent("CMD_RESUME")
                self._control_bar.set_paused(False)
                self._status_bar.showMessage(f"Running: {self._script_path}")
                self._tracer.trace_reaction_state_changed("resumed")

    @pyqtSlot()
    def _on_stop_script(self):
        """Stop script execution."""
        self._tracer.trace_action_stop_clicked()
        self._user_stopped = True
        
        if self._ipc and self._is_running:
            self._ipc.send_command(Message(msg_type=MessageType.CMD_STOP))
            self._tracer.trace_ipc_sent("CMD_STOP")

        if self._runner_process:
            self._runner_process.join(timeout=2.0)
            if self._runner_process.is_alive():
                self._runner_process.terminate()

        self._cleanup_run()

    # === M1: ANCHOR-BASED PROBE HANDLERS ===

    @pyqtSlot(object)
    def _on_probe_requested(self, anchor: ProbeAnchor):
        """Handle click-to-probe request from code viewer."""
        logger.debug(f"_on_probe_requested called with anchor: {anchor}")
        logger.debug(f"Current _probe_panels keys: {list(self._probe_panels.keys())}")
        
        if self._probe_registry.is_full():
            logger.debug("Registry is full, returning")
            self._status_bar.showMessage("Maximum probes reached (5)")
            return

        # Add to registry and get assigned color
        color = self._probe_registry.add_probe(anchor)
        logger.debug(f"Probe added, assigned color: {color.name() if color else 'None'}")
        logger.debug(f"After add, _probe_panels keys: {list(self._probe_panels.keys())}")
        
        # Initialize metadata
        if anchor not in self._probe_metadata:
            self._probe_metadata[anchor] = {
                'lens': None,
                'dtype': None
            }

        # Update code viewer
        self._code_viewer.set_probe_active(anchor, color)

        # Update gutter
        self._code_gutter.set_probed_line(anchor.line, color)

        # Create probe panel
        panel = self._probe_container.create_probe_panel(anchor, color)
        self._probe_panels[anchor] = panel
        
        # M2: Connect lens changed signal tracking
        if hasattr(panel, '_lens_dropdown') and panel._lens_dropdown:
            from functools import partial
            panel._lens_dropdown.lens_changed.connect(
                partial(self._on_lens_changed, anchor)
            )
            
            # If we have a stored lens preference, apply it
            stored_lens = self._probe_metadata[anchor].get('lens')
            if stored_lens:
                panel._lens_dropdown.set_lens(stored_lens)

        # Send to runner if running
        if self._ipc and self._is_running:
            msg = make_add_probe_cmd(anchor)
            self._ipc.send_command(msg)

        self._status_bar.showMessage(f"Probe added: {anchor.identity_label()}")

    @pyqtSlot(object)
    def _on_probe_remove_requested(self, anchor: ProbeAnchor):
        """Handle probe removal request."""
        logger.debug(f"_on_probe_remove_requested called with anchor: {anchor}")
        logger.debug(f"Current _probe_panels keys: {list(self._probe_panels.keys())}")
        logger.debug(f"anchor in _probe_panels: {anchor in self._probe_panels}")
        logger.debug(f"Active probes in code_viewer: {list(self._code_viewer._active_probes.keys())}")
        
        if anchor not in self._probe_panels:
            logger.debug("Anchor not in _probe_panels, returning early")
            return

        panel = self._probe_panels[anchor]

        # Animate removal
        ProbeAnimations.fade_out(panel, on_finished=lambda: self._complete_probe_removal(anchor))

    def _complete_probe_removal(self, anchor: ProbeAnchor):
        """Complete probe removal after animation."""
        logger.debug(f"_complete_probe_removal called with anchor: {anchor}")
        
        # Remove from registry
        self._probe_registry.remove_probe(anchor)
        logger.debug(f"Removed from registry")

        # Update code viewer
        self._code_viewer.remove_probe(anchor)

        # Update gutter
        self._code_gutter.clear_probed_line(anchor.line)

        # Remove panel
        if anchor in self._probe_panels:
            panel = self._probe_panels.pop(anchor)
            self._probe_container.remove_probe_panel(anchor)

        # Send to runner if running
        if self._ipc and self._is_running:
            msg = make_remove_probe_cmd(anchor)
            self._ipc.send_command(msg)

        self._status_bar.showMessage(f"Probe removed: {anchor.identity_label()}")

        self._status_bar.showMessage(f"Probe removed: {anchor.identity_label()}")

    @pyqtSlot(object, str)
    def _on_lens_changed(self, anchor: ProbeAnchor, lens_name: str):
        """Handle lens change from probe panel."""
        if anchor in self._probe_metadata:
            self._probe_metadata[anchor]['lens'] = lens_name
            logger.debug(f"Lens preference saved for {anchor.identity_label()}: {lens_name}")

    @pyqtSlot(str)
    def _on_file_changed(self, filepath: str):
        """Handle file modification detected by file watcher."""
        if filepath != self._script_path:
            return

        # Get old and new source
        old_source = self._last_source_content or ""
        try:
            with open(filepath, 'r') as f:
                new_source = f.read()
        except (IOError, OSError):
            return

        # Map anchors to new positions
        mapper = AnchorMapper(old_source, new_source, filepath)
        active_anchors = self._probe_registry.active_anchors

        # Find invalidated anchors
        invalid = mapper.get_invalidated(list(active_anchors))

        # Mark invalid anchors
        for anchor in invalid:
            self._code_viewer.set_probe_invalid(anchor)
            if anchor in self._probe_panels:
                self._probe_panels[anchor].set_state(ProbeState.INVALID)

        self._probe_registry.invalidate_anchors(invalid)

        # Reload file in viewer
        self._code_viewer.reload_file()
        self._last_source_content = self._code_viewer.toPlainText()

        # Re-apply valid probe highlights
        for anchor in active_anchors - invalid:
            color = self._probe_registry.get_color(anchor)
            if color:
                self._code_viewer.set_probe_active(anchor, color)
                self._code_gutter.set_probed_line(anchor.line, color)

        if invalid:
            self._status_bar.showMessage(f"File changed: {len(invalid)} probe(s) invalidated")

    @pyqtSlot(object, object)
    def _on_probe_state_changed(self, anchor: ProbeAnchor, state: ProbeState):
        """Handle probe state change from registry."""
        if anchor in self._probe_panels:
            self._probe_panels[anchor].set_state(state)

    @pyqtSlot()
    def _on_script_ended(self):
        """Handle script completion."""
        logger.debug("_on_script_ended called")
        self._tracer.trace_ipc_received("script_ended signal", {})
        self._status_bar.showMessage("Script finished")
        
        # Check loop BEFORE cleanup to decide how to handle
        should_loop = self._control_bar.is_loop_enabled and not self._user_stopped
        logger.debug(f"  is_loop_enabled={self._control_bar.is_loop_enabled}, user_stopped={self._user_stopped}, should_loop={should_loop}")
        
        if should_loop:
            # Soft cleanup: terminate process but don't close IPC or reset UI
            logger.debug("  -> taking loop path")
            self._tracer.trace_reaction_state_changed(f"script ended, looping (loop_enabled={self._control_bar.is_loop_enabled}, user_stopped={self._user_stopped})")
            self._soft_cleanup_for_loop()
            # Restart with small delay for process cleanup
            QTimer.singleShot(50, self._restart_loop)
        else:
            # Full cleanup when not looping
            logger.debug("  -> taking cleanup path")
            self._tracer.trace_reaction_state_changed(f"script ended, stopping (loop_enabled={self._control_bar.is_loop_enabled}, user_stopped={self._user_stopped})")
            self._cleanup_run()

    @pyqtSlot(dict)
    def _on_exception(self, payload: dict):
        """Handle exception from script."""
        QMessageBox.critical(
            self,
            f"Exception: {payload['type']}",
            f"{payload['message']}\n\n{payload['traceback']}"
        )
        self._cleanup_run()

    def _soft_cleanup_for_loop(self):
        """Clean up subprocess for loop restart without closing IPC."""
        logger.debug("_soft_cleanup_for_loop called")
        self._tracer.trace_reaction_cleanup("soft cleanup for loop")
        self._is_running = False
        self._poll_timer.stop()
        self._fps_timer.stop()
        
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
            self._tracer.trace_reaction_subprocess_ended(proc.exitcode)
        self._runner_process = None
        logger.debug(f"  IPC still valid: {self._ipc is not None}")
        # Note: IPC channel stays open, UI stays in running state

    def _restart_loop(self):
        """Restart script for loop mode with existing IPC."""
        logger.debug("_restart_loop called")
        if not self._script_path or not self._ipc:
            logger.debug(f"  ABORT: script_path={self._script_path}, ipc={self._ipc}")
            self._cleanup_run()  # Fallback to full cleanup
            return
        
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
        self._tracer.trace_loop_restart(self._loop_count)
        self._tracer.trace_reaction_subprocess_started(self._runner_process.pid)
        
        # Re-send probe commands for the new subprocess
        for anchor in self._probe_registry.active_anchors:
            msg = make_add_probe_cmd(anchor)
            self._ipc.send_command(msg)
        
        # Resume polling
        self._is_running = True
        self._poll_timer.start()
        self._fps_timer.start()
        logger.debug(f"  loop restart complete, _is_running={self._is_running}")
        
        self._status_bar.showMessage(f"Looping: {self._script_path}")

    def _cleanup_run(self):
        """Clean up after script run."""
        self._tracer.trace_reaction_cleanup("full cleanup started")
        
        # Stop everything first
        self._is_running = False
        self._poll_timer.stop()
        self._fps_timer.stop()

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
            self._tracer.trace_reaction_subprocess_ended(proc.exitcode)

        # Clean up IPC (drains queues and closes shared memory)
        ipc = self._ipc
        if ipc is not None:
            ipc.cleanup()

        self._ipc = None
        self._runner_process = None
        self._control_bar.set_running(False)
        self._status_bar.showMessage("Ready")
        self._tracer.trace_reaction_state_changed("cleanup complete, now IDLE")

    def closeEvent(self, event):
        """Handle window close."""
        self._on_stop_script()
        super().closeEvent(event)
