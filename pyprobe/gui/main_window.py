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

from pyprobe.logging import get_logger, trace_print
logger = get_logger(__name__)

from .probe_panel import ProbePanel
from .panel_container import ProbePanelContainer
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

# === M2.5 IMPORTS ===
from .dock_bar import DockBar
from .script_runner import ScriptRunner
from .message_handler import MessageHandler
from .probe_controller import ProbeController
from .scalar_watch_window import ScalarWatchWindow


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

        # M1: Probe panels by anchor - managed by ProbeController
        # Direct references to _probe_panels delegate to controller

        # FPS tracking
        self._frame_count = 0
        self._fps = 0.0

        # M1: Source file content cache for anchor mapping
        self._last_source_content: Optional[str] = None

        self._setup_ui()
        self._setup_signals()

        # Apply cyberpunk theme
        apply_cyberpunk_theme(self)
        
        # Initialize state tracer
        self._tracer = get_tracer()
        self._tracer.set_main_window(self)
        self._loop_count = 0  # Track loop iterations for tracing

        # Initialize ScriptRunner and MessageHandler
        self._script_runner = ScriptRunner(self)
        self._message_handler = MessageHandler(self._script_runner, self._tracer, self)
        self._setup_script_runner()
        self._setup_message_handler()
        self._setup_fps_timer()
        
        # Initialize ProbeController (after UI setup)
        self._probe_controller = ProbeController(
            registry=self._probe_registry,
            container=self._probe_container,
            code_viewer=self._code_viewer,
            gutter=self._code_gutter,
            get_ipc=lambda: self._script_runner.ipc,
            get_is_running=lambda: self._script_runner.is_running,
            parent=self
        )
        self._setup_probe_controller()

        # Load script if provided
        if script_path:
            self._load_script(script_path)
    
    @property
    def _probe_panels(self) -> Dict[ProbeAnchor, ProbePanel]:
        """Delegate to ProbeController's probe_panels."""
        return self._probe_controller.probe_panels
    
    @property
    def _probe_metadata(self) -> Dict[ProbeAnchor, dict]:
        """Delegate to ProbeController's probe_metadata."""
        return self._probe_controller.probe_metadata

    def _setup_ui(self):
        """Create the UI layout."""
        self.setWindowTitle("PyProbe - Variable Probe")
        self.setMinimumSize(1200, 800)

        # Central widget with splitter
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # M2.5: Wrap splitter + dock bar in a vertical layout
        from PyQt6.QtWidgets import QVBoxLayout as _QVBox
        main_vlayout = _QVBox()
        main_vlayout.setContentsMargins(0, 0, 0, 0)
        main_vlayout.setSpacing(0)
        layout.addLayout(main_vlayout)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_vlayout.addWidget(splitter)

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

        # M2.5: Dock bar at bottom (hidden when empty)
        self._dock_bar = DockBar(self)
        self._dock_bar.setVisible(False)
        main_vlayout.addWidget(self._dock_bar)
        
        # Scalar watch window (floating, created lazily)
        self._scalar_watch_window: Optional[ScalarWatchWindow] = None

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
        self._control_bar.watch_clicked.connect(self._on_toggle_watch_window)

        # === M1: Code viewer signals ===
        self._code_viewer.probe_requested.connect(self._on_probe_requested)
        self._code_viewer.probe_removed.connect(self._on_probe_remove_requested)
        self._code_viewer.watch_probe_requested.connect(self._on_watch_probe_requested)

        # === M1: File watcher signals ===
        self._file_watcher.file_changed.connect(self._on_file_changed)

        # === M1: Probe registry signals ===
        self._probe_registry.probe_state_changed.connect(self._on_probe_state_changed)

        # Internal signals (for thread-safe GUI updates)
        self.variable_received.connect(self._on_variable_data)
        self.script_ended.connect(self._on_script_ended)
        self.exception_occurred.connect(self._on_exception)

        # M2.5: Dock bar restore
        self._dock_bar.panel_restore_requested.connect(self._on_dock_bar_restore)
        
        # M2.5: Layout manager maximize/restore via dock bar
        lm = self._probe_container.layout_manager
        lm.panel_park_requested.connect(self._on_panel_park_requested)
        lm.panel_unpark_requested.connect(self._on_dock_bar_restore_anchor)

    def _setup_fps_timer(self):
        """Set up timer for FPS counter."""
        self._fps_timer = QTimer()
        self._fps_timer.timeout.connect(self._update_fps)
        self._fps_timer.setInterval(1000)  # Every second

    def _setup_message_handler(self):
        """Connect MessageHandler signals to slots."""
        self._message_handler.probe_value.connect(self._on_probe_value)
        self._message_handler.probe_value_batch.connect(self._on_probe_value_batch)
        self._message_handler.script_ended.connect(self._on_script_ended)
        self._message_handler.exception_raised.connect(self._on_exception)
        self._message_handler.variable_data.connect(self._on_variable_data)

    def _setup_script_runner(self):
        """Configure the script runner with callbacks and connect signals."""
        # Connect signals from ScriptRunner
        self._script_runner.started.connect(self._on_runner_started)
        self._script_runner.ended.connect(self._on_runner_ended)
        self._script_runner.loop_restarted.connect(self._on_loop_restarted)

    def _setup_probe_controller(self):
        """Connect ProbeController signals to slots."""
        self._probe_controller.status_message.connect(self._status_bar.showMessage)

    @pyqtSlot(dict)
    def _on_probe_value(self, payload: dict):
        """Handle single probe value from MessageHandler."""
        anchor = ProbeAnchor.from_dict(payload['anchor'])
        self._probe_registry.update_data_received(anchor)
        
        # Update the anchor's own panel if it exists
        if anchor in self._probe_panels:
            # Update metadata dtype
            if anchor in self._probe_metadata:
                self._probe_metadata[anchor]['dtype'] = payload['dtype']
            
            self._probe_panels[anchor].update_data(
                value=payload['value'],
                dtype=payload['dtype'],
                shape=payload.get('shape'),
            )
        
        # Route to scalar watch window if it exists and has this anchor
        if self._scalar_watch_window and self._scalar_watch_window.has_scalar(anchor):
            self._scalar_watch_window.update_scalar(anchor, payload['value'])
        
        # M2.5: Forward overlay data to target panels
        self._forward_overlay_data(anchor, payload)

    @pyqtSlot(list)
    def _on_probe_value_batch(self, probes: list):
        """Handle batched probe values from MessageHandler."""
        for probe_data in probes:
            anchor = ProbeAnchor.from_dict(probe_data['anchor'])
            self._probe_registry.update_data_received(anchor)
            if anchor in self._probe_panels:
                self._probe_panels[anchor].update_data(
                    value=probe_data['value'],
                    dtype=probe_data['dtype'],
                    shape=probe_data.get('shape'),
                )
            
            # Route to scalar watch window if it exists and has this anchor
            if self._scalar_watch_window and self._scalar_watch_window.has_scalar(anchor):
                self._scalar_watch_window.update_scalar(anchor, probe_data['value'])
            
            # M2.5: Forward overlay data to target panels
            self._forward_overlay_data(anchor, probe_data)

    def _update_fps(self):
        """Update FPS display."""
        self._fps = self._message_handler.reset_frame_count()

        if self._script_runner.is_running:
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
        if not self._script_runner.is_running:
             self._on_run_script()
        else:
             self._on_pause_script()

    @pyqtSlot()
    def _on_run_script(self):
        """Start running the loaded script."""
        if not self._script_path:
            return
        
        # Configure and start the script runner
        self._script_runner.configure(
            script_path=self._script_path,
            get_active_anchors=lambda: list(self._probe_registry.active_anchors),
            tracer=self._tracer
        )
        
        if self._script_runner.start():
            # Start polling timers
            self._message_handler.start_polling()
            self._fps_timer.start()
            self._status_bar.showMessage(f"Running: {self._script_path}")
            self._control_bar.set_running(True)

    @pyqtSlot()
    def _on_pause_script(self):
        """Pause/resume script execution."""
        is_paused = self._script_runner.toggle_pause()
        self._control_bar.set_paused(is_paused)
        if is_paused:
            self._status_bar.showMessage("Paused")
        else:
            self._status_bar.showMessage(f"Running: {self._script_path}")

    @pyqtSlot()
    def _on_stop_script(self):
        """Stop script execution."""
        self._script_runner.stop()
        # UI updates handled in _on_runner_ended signal handler

    @pyqtSlot()
    def _on_toggle_watch_window(self):
        """Toggle the scalar watch window visibility."""
        if self._scalar_watch_window is None:
            # Create and show the watch window
            self._scalar_watch_window = ScalarWatchWindow()
            self._scalar_watch_window.scalar_removed.connect(self._on_watch_scalar_removed)
            self._scalar_watch_window.show()
        elif self._scalar_watch_window.isVisible():
            self._scalar_watch_window.hide()
        else:
            self._scalar_watch_window.show()
            self._scalar_watch_window.raise_()  # Bring to front

    # === M1: ANCHOR-BASED PROBE HANDLERS ===

    @pyqtSlot(object)
    def _on_probe_requested(self, anchor: ProbeAnchor):
        """Handle click-to-probe request from code viewer."""
        panel = self._probe_controller.add_probe(anchor)
        if panel:
            # Mark as graphical probe in code viewer
            self._code_viewer.set_probe_graphical(anchor)
            # M2.5: Connect park and overlay signals
            panel.park_requested.connect(lambda a=anchor: self._on_panel_park_requested(a))
            panel.overlay_requested.connect(self._on_overlay_requested)
            panel.overlay_remove_requested.connect(self._on_overlay_remove_requested)

    @pyqtSlot(object)
    def _on_watch_probe_requested(self, anchor: ProbeAnchor):
        """Handle Alt+click to add/remove scalar from watch window (toggle)."""
        # Create watch window lazily
        if self._scalar_watch_window is None:
            self._scalar_watch_window = ScalarWatchWindow()
            self._scalar_watch_window.scalar_removed.connect(self._on_watch_scalar_removed)
        
        # Toggle behavior: if already watching, remove it
        if self._scalar_watch_window.has_scalar(anchor):
            self._scalar_watch_window.remove_scalar(anchor)
            logger.debug(f"Removed {anchor.symbol} from scalar watch window (toggle)")
            return
        
        # Get a color for the scalar (or assign one)
        color = self._probe_registry.get_color(anchor)
        if color is None:
            # Register the probe to get a color
            color = self._probe_registry.add_probe(anchor)
            if color is None:
                color = QColor('#00ffff')
        
        # Add to watch window
        self._scalar_watch_window.add_scalar(anchor, color)
        
        # Highlight in code viewer
        self._code_viewer.set_probe_active(anchor, color)
        
        # Send probe command to subprocess if running
        ipc = self._script_runner.ipc
        if ipc and self._script_runner.is_running:
            msg = make_add_probe_cmd(anchor)
            ipc.send_command(msg)
        
        logger.debug(f"Added {anchor.symbol} to scalar watch window")

    @pyqtSlot(object)
    def _on_watch_scalar_removed(self, anchor: ProbeAnchor):
        """Handle removal of scalar from watch window."""
        # Clear from code viewer highlight
        self._code_viewer.remove_probe(anchor)
        # Release from registry
        self._probe_registry.remove_probe(anchor)
        
        # Send remove probe command to subprocess if running
        ipc = self._script_runner.ipc
        if ipc and self._script_runner.is_running:
            msg = make_remove_probe_cmd(anchor)
            ipc.send_command(msg)
        
        logger.debug(f"Removed {anchor.symbol} from scalar watch window")

    @pyqtSlot(object)
    def _on_probe_remove_requested(self, anchor: ProbeAnchor):
        """Handle probe removal request."""
        # Mark as no longer graphical in code viewer
        self._code_viewer.unset_probe_graphical(anchor)
        self._probe_controller.remove_probe(anchor)

    def _complete_probe_removal(self, anchor: ProbeAnchor):
        """Complete probe removal after animation."""
        self._probe_controller.complete_probe_removal(anchor)

    def _on_lens_changed(self, anchor: ProbeAnchor, lens_name: str):
        """Handle lens change from probe panel."""
        self._probe_controller.handle_lens_changed(anchor, lens_name)

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
        should_loop = self._control_bar.is_loop_enabled and not self._script_runner.user_stopped
        logger.debug(f"  is_loop_enabled={self._control_bar.is_loop_enabled}, user_stopped={self._script_runner.user_stopped}, should_loop={should_loop}")
        
        if should_loop:
            # Soft cleanup: terminate process but don't close IPC or reset UI
            logger.debug("  -> taking loop path")
            self._tracer.trace_reaction_state_changed(f"script ended, looping")
            self._message_handler.stop_polling()
            self._fps_timer.stop()
            self._script_runner.soft_cleanup_for_loop()
            # Restart with small delay for process cleanup
            QTimer.singleShot(50, self._do_restart_loop)
        else:
            # Full cleanup when not looping
            logger.debug("  -> taking cleanup path")
            self._tracer.trace_reaction_state_changed(f"script ended, stopping")
            self._message_handler.stop_polling()
            self._fps_timer.stop()
            self._script_runner.cleanup()
            self._control_bar.set_running(False)
            self._status_bar.showMessage("Ready")

    def _do_restart_loop(self):
        """Restart script for loop mode (called after delay)."""
        if self._script_runner.restart_loop():
            self._message_handler.start_polling()
            self._fps_timer.start()
            self._status_bar.showMessage(f"Looping: {self._script_path}")
        else:
            self._control_bar.set_running(False)
            self._status_bar.showMessage("Ready")

    @pyqtSlot(dict)
    def _on_exception(self, payload: dict):
        """Handle exception from script."""
        QMessageBox.critical(
            self,
            f"Exception: {payload['type']}",
            f"{payload['message']}\n\n{payload['traceback']}"
        )
        self._script_runner.cleanup()
        self._control_bar.set_running(False)
        self._status_bar.showMessage("Ready")

    # === ScriptRunner Signal Handlers ===

    def _on_runner_started(self):
        """Handle ScriptRunner started signal."""
        logger.debug("ScriptRunner started signal received")

    def _on_runner_ended(self):
        """Handle ScriptRunner ended signal."""
        logger.debug("ScriptRunner ended signal received")
        self._message_handler.stop_polling()
        self._fps_timer.stop()
        self._control_bar.set_running(False)
        self._status_bar.showMessage("Ready")

    def _on_loop_restarted(self, loop_count: int):
        """Handle ScriptRunner loop restarted signal."""
        logger.debug(f"ScriptRunner loop restarted, count={loop_count}")

    def closeEvent(self, event):
        """Handle window close."""
        self._on_stop_script()
        super().closeEvent(event)

    # === M2.5: Park / Restore / Overlay ===

    def _on_panel_park_requested(self, anchor: ProbeAnchor) -> None:
        """Park a panel to the dock bar."""
        if anchor not in self._probe_panels:
            return

        panel = self._probe_panels[anchor]
        panel.hide()

        # Mark panel as parked and relayout remaining panels
        self._probe_container.park_panel(anchor)

        # Add to dock bar
        anchor_key = anchor.identity_label()
        color = self._probe_registry.get_color(anchor)
        self._dock_bar.add_panel(anchor_key, anchor.symbol, color or QColor('#00ffff'))
        self._dock_bar.setVisible(True)

        logger.debug(f"Panel parked: {anchor_key}")
        self._status_bar.showMessage(f"Parked: {anchor.symbol}")

    def _on_dock_bar_restore(self, anchor_key: str) -> None:
        """Restore a panel from the dock bar."""
        # Find the panel matching this anchor_key
        for anchor, panel in self._probe_panels.items():
            if anchor.identity_label() == anchor_key:
                panel.show()
                self._dock_bar.remove_panel(anchor_key)
                # Unpark and relayout all panels including restored one
                self._probe_container.unpark_panel(anchor)
                logger.debug(f"Panel restored: {anchor_key}")
                self._status_bar.showMessage(f"Restored: {anchor.symbol}")
                break

    def _on_dock_bar_restore_anchor(self, anchor: ProbeAnchor) -> None:
        """Restore a panel from the dock bar by anchor (for layout manager)."""
        self._on_dock_bar_restore(anchor.identity_label())

    def _on_overlay_requested(self, target_panel: ProbePanel, overlay_anchor: ProbeAnchor) -> None:
        """Handle overlay drop request - delegate to ProbeController."""
        self._probe_controller.handle_overlay_requested(target_panel, overlay_anchor)

    def _forward_overlay_data(self, anchor: ProbeAnchor, payload: dict) -> None:
        """Forward overlay probe data - delegate to ProbeController."""
        self._probe_controller.forward_overlay_data(anchor, payload)

    def _on_overlay_remove_requested(self, target_panel: ProbePanel, overlay_anchor: ProbeAnchor) -> None:
        """Handle overlay removal request - delegate to ProbeController."""
        self._probe_controller.remove_overlay(target_panel, overlay_anchor)
