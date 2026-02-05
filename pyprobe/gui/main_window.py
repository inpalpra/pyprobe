"""
Main application window with probe panels and controls.
"""

from typing import Dict, List, Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QStatusBar, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
import multiprocessing as mp
import os

from .watch_list import WatchListWidget
from .probe_panel import ProbePanelContainer, ProbePanel
from .control_bar import ControlBar
from .theme.cyberpunk import apply_cyberpunk_theme
from ..ipc.channels import IPCChannel
from ..ipc.messages import Message, MessageType, make_add_watch_cmd
from ..core.runner import run_script_subprocess


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

        # Probe panels by variable name
        self._probe_panels: Dict[str, ProbePanel] = {}

        # FPS tracking
        self._frame_count = 0
        self._fps = 0.0

        self._setup_ui()
        self._setup_signals()
        self._setup_polling_timer()

        # Apply cyberpunk theme
        apply_cyberpunk_theme(self)

        # Load script if provided
        if script_path:
            self._load_script(script_path)

        # Add default watch variables
        if watch_variables:
            for var_name in watch_variables:
                self._watch_list.add_variable_programmatically(var_name)

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

        # Watch list (left panel)
        self._watch_list = WatchListWidget()
        self._watch_list.setMaximumWidth(300)
        splitter.addWidget(self._watch_list)

        # Probe panel container (right panel)
        self._probe_container = ProbePanelContainer()
        splitter.addWidget(self._probe_container)

        splitter.setSizes([250, 950])

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
        self._control_bar.open_clicked.connect(self._on_open_script)
        self._control_bar.run_clicked.connect(self._on_run_script)
        self._control_bar.pause_clicked.connect(self._on_pause_script)
        self._control_bar.stop_clicked.connect(self._on_stop_script)

        # Watch list signals
        self._watch_list.variable_added.connect(self._on_add_watch)
        self._watch_list.variable_removed.connect(self._on_remove_watch)

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
        if self._ipc is None:
            return

        # Process up to 100 messages per frame to avoid GUI freeze
        for _ in range(100):
            # Check again in case cleanup happened during loop
            if self._ipc is None:
                break

            try:
                msg = self._ipc.receive_data(timeout=0.001)
            except (AttributeError, OSError):
                # IPC was cleaned up or queue closed
                break

            if msg is None:
                break

            self._handle_message(msg)

    def _handle_message(self, msg: Message):
        """Handle an incoming message from the runner."""
        if msg.msg_type == MessageType.DATA_VARIABLE:
            self._frame_count += 1
            # Emit signal for thread-safe GUI update
            self.variable_received.emit(msg.payload)

        elif msg.msg_type == MessageType.DATA_SCRIPT_END:
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

    @pyqtSlot()
    def _on_run_script(self):
        """Start running the loaded script."""
        if not self._script_path:
            return

        # Create IPC channel
        self._ipc = IPCChannel(is_gui_side=True)

        # Get initial watch list to pass to subprocess
        initial_watches = list(self._watch_list.get_watched_variables())

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

        # Start polling timer
        self._poll_timer.start()
        self._fps_timer.start()

        self._status_bar.showMessage(f"Running: {self._script_path}")
        self._control_bar.set_running(True)

    @pyqtSlot()
    def _on_pause_script(self):
        """Pause/resume script execution."""
        if self._ipc:
            if self._control_bar.is_paused:
                self._ipc.send_command(Message(msg_type=MessageType.CMD_PAUSE))
                self._status_bar.showMessage("Paused")
            else:
                self._ipc.send_command(Message(msg_type=MessageType.CMD_RESUME))
                self._status_bar.showMessage(f"Running: {self._script_path}")

    @pyqtSlot()
    def _on_stop_script(self):
        """Stop script execution."""
        if self._ipc:
            self._ipc.send_command(Message(msg_type=MessageType.CMD_STOP))

        if self._runner_process:
            self._runner_process.join(timeout=2.0)
            if self._runner_process.is_alive():
                self._runner_process.terminate()

        self._cleanup_run()

    @pyqtSlot(str)
    def _on_add_watch(self, var_name: str):
        """Add a variable to the watch list."""
        if self._ipc:
            msg = make_add_watch_cmd(var_name)
            self._ipc.send_command(msg)

    @pyqtSlot(str)
    def _on_remove_watch(self, var_name: str):
        """Remove a variable from the watch list."""
        if self._ipc:
            msg = Message(
                msg_type=MessageType.CMD_REMOVE_WATCH,
                payload={'var_name': var_name}
            )
            self._ipc.send_command(msg)

        # Remove probe panel
        if var_name in self._probe_panels:
            self._probe_container.remove_panel(var_name)
            del self._probe_panels[var_name]

    @pyqtSlot()
    def _on_script_ended(self):
        """Handle script completion."""
        self._status_bar.showMessage("Script finished")
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

    def _cleanup_run(self):
        """Clean up after script run."""
        self._poll_timer.stop()
        self._fps_timer.stop()

        if self._ipc:
            self._ipc.cleanup()
            self._ipc = None

        self._runner_process = None
        self._control_bar.set_running(False)

    def closeEvent(self, event):
        """Handle window close."""
        self._on_stop_script()
        super().closeEvent(event)
