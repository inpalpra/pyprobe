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
from PyQt6.QtGui import QColor, QAction, QActionGroup
import multiprocessing as mp
import os
import sys

from pyprobe.logging import get_logger, trace_print
logger = get_logger(__name__)

from .probe_panel import ProbePanel
from .panel_container import ProbePanelContainer
from .control_bar import ControlBar
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
from .scalar_watch_window import ScalarWatchSidebar
from .redraw_throttler import RedrawThrottler
from .file_tree import FileTreePanel
from .collapsible_pane import CollapsiblePane

# === PERSISTENCE IMPORTS ===
from ..core.probe_persistence import (
    load_probe_settings, save_probe_settings, ProbeSettings, ProbeSpec, WatchSpec, OverlaySpec
)
from ..core.settings import set_setting
from .theme.theme_manager import ThemeManager


# Splitter pane indices — update these when adding/removing panes.
SPLIT_TREE = 0
SPLIT_CODE = 1
SPLIT_PROBES = 2
SPLIT_WATCH = 3


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

    def __init__(
        self,
        script_path: Optional[str] = None,
        probes: Optional[List[str]] = None,
        watches: Optional[List[str]] = None,
        overlays: Optional[List[str]] = None,
        auto_run: bool = False,
        auto_quit: bool = False,
        auto_quit_timeout: Optional[float] = None
    ):
        super().__init__()

        self._script_path: Optional[str] = script_path
        self._run_target_path: Optional[str] = None
        self._explicit_run_target: bool = False
        self._folder_path: Optional[str] = None
        self._cli_probes = probes or []
        self._cli_watches = watches or []
        self._cli_overlays = overlays or []
        self._auto_run = auto_run
        self._auto_quit = auto_quit
        self._auto_quit_timeout = auto_quit_timeout
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
        
        # Initialize state tracer
        self._tracer = get_tracer()
        self._tracer.set_main_window(self)
        self._loop_count = 0  # Track loop iterations for tracing

        # Initialize ScriptRunner and MessageHandler
        self._script_runner = ScriptRunner(self)
        self._message_handler = MessageHandler(self._script_runner, self._tracer, self)
        self._redraw_throttler = RedrawThrottler()
        self._setup_script_runner()
        self._setup_message_handler()
        self._setup_fps_timer()
        self._setup_auto_quit_timeout()

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
            self._explicit_run_target = True
            self._run_target_path = os.path.abspath(script_path)
            self._load_script(script_path)
    
    @property
    def _probe_panels(self) -> Dict[ProbeAnchor, List[ProbePanel]]:
        """Delegate to ProbeController's probe_panels."""
        return self._probe_controller.probe_panels
    
    @property
    def _probe_metadata(self) -> Dict[ProbeAnchor, dict]:
        """Delegate to ProbeController's probe_metadata."""
        return self._probe_controller.probe_metadata

    def _process_cli_probes(self):
        """Process CLI probe and watch arguments."""
        if not self._script_path:
            return

        def parse_target(target_str: str) -> dict:
            # Formats:
            # 1. line:symbol (instance=1, color=None, lens=None)
            # 2. line:symbol:instance (color=None, lens=None)
            # 3. line:symbol:color (instance=1, lens=None)
            # 4. line:symbol:color:lens (instance=1)
            parts = target_str.split(':')
            if len(parts) >= 2:
                try:
                    result = {
                        "line": int(parts[0]),
                        "symbol": parts[1],
                        "instance": 1,
                        "color": None,
                        "lens": None
                    }
                    if len(parts) == 3:
                        # Could be instance (int) or color (hex/name)
                        try:
                            result["instance"] = int(parts[2])
                        except ValueError:
                            result["color"] = parts[2]
                    elif len(parts) >= 4:
                        result["color"] = parts[2]
                        result["lens"] = parts[3]
                    return result
                except ValueError:
                    pass
            logger.warning(f"Invalid probe format: {target_str}")
            return None

        # Deduplicate CLI lists (tests might append same probes as loaded sidecars)
        self._cli_probes = list(dict.fromkeys(self._cli_probes))
        self._cli_watches = list(dict.fromkeys(self._cli_watches))
        self._cli_overlays = list(dict.fromkeys(self._cli_overlays))

        # Process graphical probes
        seen_probe_locs = set()
        for probe_str in self._cli_probes:
            target = parse_target(probe_str)
            if not target:
                continue
            
            line = target["line"]
            symbol = target["symbol"]
            instance = target["instance"]
            color_str = target["color"]
            lens_str = target["lens"]
            
            logger.debug(f"Processing CLI probe: {symbol} at line {line}")
            
            # Find variable instance
            vars_on_line = self._code_viewer.ast_locator.get_all_variables_on_line(line)
            matches = [v for v in vars_on_line if v.name == symbol]
            matches.sort(key=lambda v: v.col_start)
            
            if 1 <= instance <= len(matches):
                var_loc = matches[instance - 1]
                
                # Deduplicate by line/col immediately to prevent doubling
                if (line, var_loc.col_start) in seen_probe_locs:
                    continue
                seen_probe_locs.add((line, var_loc.col_start))
                
                # Create anchor
                func_name = self._code_viewer.ast_locator.get_enclosing_function(line) or ""
                anchor = ProbeAnchor(
                    file=self._script_path,
                    line=line,
                    col=var_loc.col_start,
                    symbol=symbol,
                    func=func_name,
                    is_assignment=var_loc.is_lhs
                )
                
                # Apply color mapping if specified
                if color_str:
                    logger.debug(f"Reserving color {color_str} for {symbol}")
                    color = QColor(color_str)
                    if color.isValid():
                        self._probe_registry._color_manager.reserve_color(anchor, color)
                
                # Add probe
                self._on_probe_requested(anchor)
                
                # Apply lens if specified
                if lens_str and anchor in self._probe_controller._probe_metadata:
                    self._probe_controller._probe_metadata[anchor]['lens'] = lens_str
                    
                logger.info(f"Added CLI probe for {symbol} at {line}:{var_loc.col_start}")
            else:
                logger.warning(f"Could not find instance {instance} of {symbol} on line {line}")

        # Process watches
        for watch_str in self._cli_watches:
            target = parse_target(watch_str)
            if not target:
                continue
            
            line = target["line"]
            symbol = target["symbol"]
            instance = target["instance"]
            logger.debug(f"Processing CLI watch: {symbol} at line {line}, instance {instance}")
            
            # Find variable instance
            vars_on_line = self._code_viewer.ast_locator.get_all_variables_on_line(line)
            matches = [v for v in vars_on_line if v.name == symbol]
            matches.sort(key=lambda v: v.col_start)
            
            if 1 <= instance <= len(matches):
                var_loc = matches[instance - 1]
                # Create anchor
                func_name = self._code_viewer.ast_locator.get_enclosing_function(line) or ""
                anchor = ProbeAnchor(
                    file=self._script_path,
                    line=line,
                    col=var_loc.col_start,
                    symbol=symbol,
                    func=func_name,
                    is_assignment=var_loc.is_lhs
                )
                self._on_watch_probe_requested(anchor)
                logger.info(f"Added CLI watch for {symbol} at {line}:{var_loc.col_start}")
            else:
                logger.warning(f"Could not find instance {instance} of {symbol} on line {line}")

    def _process_cli_overlays(self):
        """Process CLI overlay arguments.
        
        Format: target_symbol:line:symbol:instance
        E.g., signal_i:75:received_symbols:1
        """
        if not self._script_path:
            return

        for overlay_str in self._cli_overlays:
            parts = overlay_str.split(':')
            if len(parts) < 4:
                logger.warning(f"Invalid overlay format: {overlay_str}. Expected target_symbol:line:symbol:instance")
                continue

            target_symbol = parts[0]
            try:
                line = int(parts[1])
                symbol = parts[2]
                instance = int(parts[3]) if len(parts) > 3 else 1
            except ValueError:
                logger.warning(f"Invalid overlay format: {overlay_str}")
                continue

            logger.debug(f"Processing CLI overlay: {symbol}@{line} -> {target_symbol}")

            # Find the target probe panel
            target_panel = None
            for anchor, panel_list in self._probe_panels.items():
                if anchor.symbol == target_symbol and panel_list:
                    target_panel = panel_list[0]
                    break

            if target_panel is None:
                logger.warning(f"Could not find target probe panel for {target_symbol}")
                continue

            # Find the overlay variable
            vars_on_line = self._code_viewer.ast_locator.get_all_variables_on_line(line)
            matches = [v for v in vars_on_line if v.name == symbol]
            matches.sort(key=lambda v: v.col_start)

            if 1 <= instance <= len(matches):
                var_loc = matches[instance - 1]
                func_name = self._code_viewer.ast_locator.get_enclosing_function(line) or ""
                overlay_anchor = ProbeAnchor(
                    file=self._script_path,
                    line=line,
                    col=var_loc.col_start,
                    symbol=symbol,
                    func=func_name,
                    is_assignment=var_loc.is_lhs
                )
                self._on_overlay_requested(target_panel, overlay_anchor)
                logger.info(f"Added CLI overlay: {symbol}@{line} -> {target_symbol}")
            else:
                logger.warning(f"Could not find instance {instance} of {symbol} on line {line}")

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

        # === File tree panel (collapsed until folder opened) ===
        self._file_tree = FileTreePanel()
        self._tree_pane = CollapsiblePane(
            self._file_tree, side="left",
            expand_tooltip="Show file explorer",
        )
        splitter.addWidget(self._tree_pane)

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

        # Scalar watch sidebar (collapsed until needed)
        self._scalar_watch_sidebar = ScalarWatchSidebar()
        self._watch_pane = CollapsiblePane(
            self._scalar_watch_sidebar, side="right",
            expand_tooltip="Show watch panel",
        )
        splitter.addWidget(self._watch_pane)

        # Store reference to splitter for resizing
        self._main_splitter = splitter
        splitter.setChildrenCollapsible(False)
        self._recompute_splitter_sizes()

        # M2.5: Dock bar at bottom (hidden when empty)
        self._dock_bar = DockBar(self)
        self._dock_bar.setVisible(False)
        main_vlayout.addWidget(self._dock_bar)

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

        self._setup_theme_menu()

    def _setup_theme_menu(self) -> None:
        """Create View -> Theme menu and wire runtime switching."""
        view_menu = self.menuBar().addMenu("View")
        theme_menu = view_menu.addMenu("Theme")

        self._theme_actions: dict[str, QAction] = {}
        self._theme_action_group = QActionGroup(self)
        self._theme_action_group.setExclusive(True)

        manager = ThemeManager.instance()
        current_theme_id = manager.current.id

        for theme in manager.available():
            action = QAction(theme.name, self)
            action.setCheckable(True)
            action.setChecked(theme.id == current_theme_id)
            action.triggered.connect(
                lambda checked, theme_id=theme.id: self._on_theme_selected(theme_id, checked)
            )
            self._theme_action_group.addAction(action)
            theme_menu.addAction(action)
            self._theme_actions[theme.id] = action

        manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_selected(self, theme_id: str, checked: bool) -> None:
        """Handle a user selecting a theme from the menu."""
        if not checked:
            return

        manager = ThemeManager.instance()
        try:
            manager.set_theme(theme_id)
        except ValueError:
            logger.warning(f"Unknown theme selected: {theme_id}")
            return

        set_setting("theme", theme_id)

        self._status_bar.showMessage(f"Theme: {manager.current.name}", 3000)

    @pyqtSlot(object)
    def _on_theme_changed(self, theme) -> None:
        """Sync checked theme action with current theme state."""
        if not hasattr(self, "_theme_actions"):
            return

        for theme_id, action in self._theme_actions.items():
            action.setChecked(theme_id == theme.id)

    def _setup_signals(self):
        """Connect signals and slots."""
        # Control bar signals
        self._control_bar.open_clicked.connect(self._on_open_script)
        self._control_bar.open_folder_clicked.connect(self._on_open_folder)
        self._control_bar.action_clicked.connect(self._on_action_clicked)
        self._control_bar.stop_clicked.connect(self._on_stop_script)
        # Collapsible pane signals
        self._tree_pane.toggled.connect(lambda _: self._recompute_splitter_sizes())
        self._watch_pane.toggled.connect(lambda _: self._recompute_splitter_sizes())

        # File tree signals
        self._file_tree.file_selected.connect(self._on_file_tree_selected)

        # Scalar watch sidebar
        self._scalar_watch_sidebar.scalar_removed.connect(self._on_watch_scalar_removed)
        self._scalar_watch_sidebar.scalar_removed.connect(self._save_probe_settings)

        # === M1: Code viewer signals ===
        self._code_viewer.probe_requested.connect(self._on_probe_requested)
        self._code_viewer.probe_removed.connect(self._on_probe_remove_requested)
        self._code_viewer.watch_probe_requested.connect(self._on_watch_probe_requested)
        
        # Connect addition signals for autosave
        self._code_viewer.probe_requested.connect(self._save_probe_settings)
        self._code_viewer.watch_probe_requested.connect(self._save_probe_settings)

        # === M1: File watcher signals ===
        self._file_watcher.file_changed.connect(self._on_file_changed)

        # === M1: Probe registry signals ===
        self._probe_registry.probe_state_changed.connect(self._on_probe_state_changed)
        self._probe_registry.probe_state_changed.connect(self._save_probe_settings)

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

    def _setup_auto_quit_timeout(self):
        """Set up timeout timer for forced auto-quit."""
        if self._auto_quit_timeout is not None:
            timeout_ms = int(self._auto_quit_timeout * 1000)
            logger.info(f"Auto-quit timeout set to {self._auto_quit_timeout} seconds")
            QTimer.singleShot(timeout_ms, self._force_quit)

    def _force_quit(self):
        """Force quit the application due to timeout."""
        logger.info("Auto-quit timeout reached, forcing application exit")
        self._export_plot_data()
        sys.stderr.flush()
        sys.stdout.flush()
        os._exit(0)

    def _setup_message_handler(self):
        """Connect MessageHandler signals to slots."""
        self._message_handler.probe_record.connect(self._on_probe_record)
        self._message_handler.probe_record_batch.connect(self._on_probe_record_batch)
        self._message_handler.script_ended.connect(self._on_script_ended)
        self._message_handler.exception_raised.connect(self._on_exception)
        self._message_handler.variable_data.connect(self._on_variable_data)

    @pyqtSlot(object)
    def _on_probe_record(self, record):
        """Handle single probe record from MessageHandler."""
        self._handle_probe_records([record])

    @pyqtSlot(list)
    def _on_probe_record_batch(self, records: list):
        """Handle batched probe records from MessageHandler."""
        self._handle_probe_records(records)

    def _handle_probe_records(self, records: list) -> None:
        """Store records and schedule redraws from buffers."""
        for record in records:
            print(f"DEBUG: MainWindow received data for {record.anchor.symbol}", file=sys.stderr)
            anchor = record.anchor
            self._probe_registry.update_data_received(anchor)

            if anchor in self._probe_metadata:
                self._probe_metadata[anchor]['dtype'] = record.dtype

            self._redraw_throttler.receive(record)

            if self._scalar_watch_sidebar.has_scalar(anchor):
                self._scalar_watch_sidebar.update_scalar(anchor, record.value)

            self._forward_overlay_data(anchor, {
                'value': record.value,
                'dtype': record.dtype,
                'shape': record.shape,
            })

        self._maybe_redraw()

    def _maybe_redraw(self) -> None:
        """Redraw dirty buffers at a throttled rate."""
        if not self._redraw_throttler.should_redraw():
            return

        dirty = self._redraw_throttler.get_dirty_buffers()
        for anchor, buffer in dirty.items():
            if anchor in self._probe_panels:
                for panel in self._probe_panels[anchor]:
                    panel.update_from_buffer(buffer)
        
        # Flush any pending overlay data now that plot widgets may exist
        self._probe_controller.flush_pending_overlays()

    def _force_redraw(self) -> None:
        """Redraw all dirty buffers regardless of throttle."""
        dirty = self._redraw_throttler.get_dirty_buffers()
        for anchor, buffer in dirty.items():
            if anchor in self._probe_panels:
                for panel in self._probe_panels[anchor]:
                    panel.update_from_buffer(buffer)
        
        # Flush any pending overlay data now that plot widgets may exist
        self._probe_controller.flush_pending_overlays()

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
        logger.debug(f"Received data for {anchor.symbol}")
        print(f"DEBUG: MainWindow received data for {anchor.symbol}", file=sys.stderr)
        self._probe_registry.update_data_received(anchor)

        # Update all panels for this anchor
        if anchor in self._probe_panels:
            # Update metadata dtype
            if anchor in self._probe_metadata:
                self._probe_metadata[anchor]['dtype'] = payload['dtype']

            for panel in self._probe_panels[anchor]:
                panel.update_data(
                    value=payload['value'],
                    dtype=payload['dtype'],
                    shape=payload.get('shape'),
                )

        # Route to scalar watch sidebar if it has this anchor
        if self._scalar_watch_sidebar.has_scalar(anchor):
            self._scalar_watch_sidebar.update_scalar(anchor, payload['value'])

        # M2.5: Forward overlay data to target panels
        self._forward_overlay_data(anchor, payload)

    @pyqtSlot(list)
    def _on_probe_value_batch(self, probes: list):
        """Handle batched probe values from MessageHandler."""
        for probe_data in probes:
            anchor = ProbeAnchor.from_dict(probe_data['anchor'])
            print(f"DEBUG: MainWindow received data for {anchor.symbol}", file=sys.stderr)
            self._probe_registry.update_data_received(anchor)
            if anchor in self._probe_panels:
                for panel in self._probe_panels[anchor]:
                    panel.update_data(
                        value=probe_data['value'],
                        dtype=probe_data['dtype'],
                        shape=probe_data.get('shape'),
                    )
            
            # Route to scalar watch sidebar if it has this anchor
            if self._scalar_watch_sidebar.has_scalar(anchor):
                self._scalar_watch_sidebar.update_scalar(anchor, probe_data['value'])
            
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
        start_dir = self._folder_path or ""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Python Script",
            start_dir,
            "Python Files (*.py);;All Files (*)"
        )
        if path:
            self._explicit_run_target = True
            self._run_target_path = os.path.abspath(path)
            self._load_script(path)
            if self._folder_path:
                self._file_tree.highlight_file(path)

    def _on_open_folder(self):
        """Open folder dialog for folder browsing."""
        folder = QFileDialog.getExistingDirectory(self, "Open Folder", "")
        if folder:
            self._load_folder(folder)

    def _load_folder(self, folder_path: str):
        """Load a folder into the file tree panel."""
        self._folder_path = os.path.abspath(folder_path)
        self._file_tree.set_root(self._folder_path)
        self._tree_pane.expand()
        self._status_bar.showMessage(f"Opened folder: {os.path.basename(folder_path)}")

    def _stash_current_file_visuals(self):
        """Hide visual elements for current file's probes. Registry stays intact."""
        # Save current file's probes to sidecar
        self._save_probe_settings()

        # Park (hide) probe panels for current file's anchors
        for anchor in list(self._probe_panels.keys()):
            if anchor.file == self._script_path:
                for panel in self._probe_panels[anchor]:
                    panel.hide()
                self._probe_container.park_panel(anchor)

        # Clear gutter marks (line numbers are file-specific)
        self._code_gutter.clear_all_probes()

        # Clear code viewer highlights (will be repopulated for new file)
        self._code_viewer.clear_all_probes()

        # Reset CLI probe lists (repopulated by new file's sidecar)
        self._cli_probes = []
        self._cli_watches = []
        self._cli_overlays = []

    def _restore_file_visuals(self, file_path: str):
        """Restore visual elements for a file that already has probes in the registry."""
        for anchor in list(self._probe_panels.keys()):
            if anchor.file == file_path:
                self._probe_container.unpark_panel(anchor)
                for panel in self._probe_panels[anchor]:
                    panel.show()
                color = self._probe_registry.get_color(anchor)
                if color:
                    self._code_viewer.set_probe_active(anchor, color)
                    self._code_gutter.set_probed_line(anchor.line, color)
                    # Any anchor in _probe_panels is graphical
                    self._code_viewer.set_probe_graphical(anchor)

    def _on_file_tree_selected(self, file_path: str):
        """Handle file selection from file tree."""
        abs_path = os.path.abspath(file_path)
        if abs_path == self._script_path:
            return  # already loaded

        # Stash current file's visuals (keep registry intact)
        self._stash_current_file_visuals()

        # Check if new file already has probes in registry (returning to it)
        has_stashed = any(a.file == abs_path for a in self._probe_registry.all_anchors)

        if has_stashed:
            # Quick restore: load code, show stashed panels
            self._script_path = abs_path
            if not self._explicit_run_target:
                self._run_target_path = abs_path
            self._control_bar.set_script_loaded(True, abs_path)
            self._code_viewer.load_file(abs_path)
            self._file_watcher.watch_file(abs_path)
            self._last_source_content = self._code_viewer.toPlainText()
            self._restore_file_visuals(abs_path)
        else:
            # First visit: full load from sidecar
            self._load_script(abs_path)

        self._file_tree.highlight_file(abs_path)

    def _clear_all_probes(self):
        """Remove all active probes for clean file switching."""
        # Save current probes first
        self._save_probe_settings()

        # Remove all probe panels (skip animation for bulk clear)
        for anchor in list(self._probe_panels.keys()):
            for panel in list(self._probe_panels.get(anchor, [])):
                self._probe_container.remove_probe_panel(panel=panel)
            self._code_viewer.remove_probe(anchor)
            self._code_gutter.clear_probed_line(anchor.line)
        self._probe_controller._probe_panels.clear()
        self._probe_controller._probe_metadata.clear()

        # Clear registry
        self._probe_registry.clear()

        # Clear scalar watch sidebar
        self._scalar_watch_sidebar.clear()

        # Reset CLI probe lists (will be re-populated from sidecar)
        self._cli_probes = []
        self._cli_watches = []
        self._cli_overlays = []

    def _load_script(self, path: str):
        """Load a script file."""
        self._script_path = os.path.abspath(path)
        if not self._explicit_run_target:
            self._run_target_path = self._script_path
        self._status_bar.showMessage(f"Loaded: {path}")
        self._control_bar.set_script_loaded(True, path)

        # === M1: Load into code viewer and start watching ===
        self._code_viewer.load_file(path)
        self._file_watcher.watch_file(path)
        self._last_source_content = self._code_viewer.toPlainText()

        self._load_probe_settings()

        # Process CLI probes and overlays after loading
        self._process_cli_probes()
        self._process_cli_overlays()

        # Auto-run if requested
        if self._auto_run:
            QTimer.singleShot(500, self._on_run_script)

    def _load_probe_settings(self):
        """Load probe settings from the sidecar file."""
        if not self._script_path:
            return
            
        settings = load_probe_settings(self._script_path)
        
        # Load probes
        for p in settings.probes:
            # Format: line:symbol or line:symbol:color or line:symbol:color:lens
            # We construct a cli string to reuse existing parsing logic
            cli_str = f"{p.line}:{p.symbol}"
            if p.color:
                cli_str += f":{p.color}"
                if p.lens:
                    cli_str += f":{p.lens}"
            self._cli_probes.append(cli_str)
            
        # Load watches
        for w in settings.watches:
            self._cli_watches.append(f"{w.line}:{w.symbol}")
            
        # Load overlays
        for o in settings.overlays:
            self._cli_overlays.append(f"{o.target.symbol}:{o.overlay.line}:{o.overlay.symbol}:1")
            
        logger.info(f"Loaded {len(settings.probes)} probes from sidecar")

    @pyqtSlot()
    def _save_probe_settings(self):
        """Save current probe settings to the sidecar file."""
        if not self._script_path:
            return
            
        settings = ProbeSettings()
        
        # Save active probes from registry (only those belonging to this file)
        for anchor in self._probe_registry.active_anchors:
            if anchor.file != self._script_path:
                continue  # Only save probes belonging to this file
            spec = ProbeSpec.from_anchor(anchor)
            
            # Extract color
            color = self._probe_registry.get_color(anchor)
            if color:
                spec.color = color.name()
                
            # Extract lens if available in controller metadata
            if hasattr(self, '_probe_controller') and anchor in self._probe_controller._probe_metadata:
                metadata = self._probe_controller._probe_metadata[anchor]
                # Only save active probes (not purely overlay sources)
                if metadata.get('overlay_target') is not None:
                    continue
                spec.lens = metadata.get('lens')
                
            settings.probes.append(spec)
            
        # Save watches from sidebar (only those belonging to this file)
        for anchor in self._scalar_watch_sidebar.get_watched_anchors():
            if anchor.file != self._script_path:
                continue
            settings.watches.append(WatchSpec.from_anchor(anchor))

        # Save overlays from probe controller panels (only those belonging to this file)
        if hasattr(self, '_probe_controller'):
            for target_anchor, panel_list in self._probe_controller._probe_panels.items():
                if target_anchor.file != self._script_path:
                    continue
                if not panel_list:
                    continue
                target_panel = panel_list[-1]
                if hasattr(target_panel, '_overlay_anchors'):
                    for overlay_anchor in target_panel._overlay_anchors:
                        settings.overlays.append(OverlaySpec(
                            target=ProbeSpec.from_anchor(target_anchor),
                            overlay=ProbeSpec.from_anchor(overlay_anchor)
                        ))
                        
        save_probe_settings(self._script_path, settings)

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

        # Use the run target (first loaded file) instead of currently viewed file
        run_path = self._run_target_path or self._script_path

        # Configure and start the script runner
        self._script_runner.configure(
            script_path=run_path,
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
        """Toggle the scalar watch sidebar visibility."""
        self._watch_pane.toggle()

    @pyqtSlot()
    def _on_toggle_file_tree(self):
        """Toggle the file tree panel visibility."""
        self._tree_pane.toggle()

    def _recompute_splitter_sizes(self) -> None:
        """Distribute splitter space using weight-based proportional allocation.

        Collapsed panes get 20px (edge strip only).  Remaining space is
        distributed among expanded panes according to weights:
            Explorer=1, Code=1.5, Probes=3, Watch=1
        """
        total = self._main_splitter.width() or 1200  # fallback before first show
        weights = {
            SPLIT_TREE: 1.0,
            SPLIT_CODE: 1.5,
            SPLIT_PROBES: 3.0,
            SPLIT_WATCH: 1.0,
        }

        tree_expanded = self._tree_pane.is_expanded
        watch_expanded = self._watch_pane.is_expanded

        collapsed_px = 0
        if not tree_expanded:
            collapsed_px += 20
        if not watch_expanded:
            collapsed_px += 20

        remaining = total - collapsed_px

        # Sum weights of expanded panes
        expanded_weight = 0.0
        if tree_expanded:
            expanded_weight += weights[SPLIT_TREE]
        expanded_weight += weights[SPLIT_CODE]   # code always expanded
        expanded_weight += weights[SPLIT_PROBES]  # probes always expanded
        if watch_expanded:
            expanded_weight += weights[SPLIT_WATCH]

        def alloc(idx: int) -> int:
            return int(remaining * weights[idx] / expanded_weight) if expanded_weight else 0

        sizes = [0] * 4

        # Tree pane
        if tree_expanded:
            raw = alloc(SPLIT_TREE)
            sizes[SPLIT_TREE] = max(180, min(300, raw))
        else:
            sizes[SPLIT_TREE] = 20

        # Code pane
        sizes[SPLIT_CODE] = max(200, alloc(SPLIT_CODE))

        # Probes pane (placeholder, adjusted below)
        sizes[SPLIT_PROBES] = alloc(SPLIT_PROBES)

        # Watch pane
        if watch_expanded:
            raw = alloc(SPLIT_WATCH)
            sizes[SPLIT_WATCH] = max(180, min(280, raw))
        else:
            sizes[SPLIT_WATCH] = 20

        # Push residual into probes so total matches
        residual = total - (sizes[SPLIT_TREE] + sizes[SPLIT_CODE] + sizes[SPLIT_WATCH])
        sizes[SPLIT_PROBES] = max(100, residual)

        self._main_splitter.setSizes(sizes)

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
        """Handle Alt+click to add/remove scalar from watch sidebar (toggle)."""
        # Toggle behavior: if already watching, remove it
        if self._scalar_watch_sidebar.has_scalar(anchor):
            self._scalar_watch_sidebar.remove_scalar(anchor)
            logger.debug(f"Removed {anchor.symbol} from scalar watch sidebar (toggle)")
            return
        
        # Get a color for the scalar (or assign one)
        color = self._probe_registry.get_color(anchor)
        if color is None:
            # Register the probe to get a color
            color = self._probe_registry.add_probe(anchor)
            if color is None:
                color = QColor('#00ffff')
        
        # Add to watch sidebar
        self._scalar_watch_sidebar.add_scalar(anchor, color)
        
        # Show sidebar if collapsed
        if not self._watch_pane.is_expanded:
            self._watch_pane.expand()
        
        # Highlight in code viewer
        self._code_viewer.set_probe_active(anchor, color)
        
        # Send probe command to subprocess if running
        ipc = self._script_runner.ipc
        if ipc and self._script_runner.is_running:
            msg = make_add_probe_cmd(anchor)
            ipc.send_command(msg)
        
        logger.debug(f"Added {anchor.symbol} to scalar watch sidebar")

    @pyqtSlot(object)
    def _on_watch_scalar_removed(self, anchor: ProbeAnchor):
        """Handle removal of scalar from watch sidebar."""
        # Clear from code viewer highlight
        self._code_viewer.remove_probe(anchor)
        # Release from registry
        self._probe_registry.remove_probe(anchor)
        
        # Send remove probe command to subprocess if running
        ipc = self._script_runner.ipc
        if ipc and self._script_runner.is_running:
            msg = make_remove_probe_cmd(anchor)
            ipc.send_command(msg)
        
        logger.debug(f"Removed {anchor.symbol} from scalar watch sidebar")

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
                for panel in self._probe_panels[anchor]:
                    panel.set_state(ProbeState.INVALID)

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
            for panel in self._probe_panels[anchor]:
                panel.set_state(state)

    @pyqtSlot()
    def _on_script_ended(self):
        """Handle script completion."""
        logger.debug("_on_script_ended called")
        self._tracer.trace_ipc_received("script_ended signal", {})
        self._status_bar.showMessage("Script finished")

        # Ensure final buffered data is rendered after fast runs
        self._force_redraw()
        
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

            # Auto-quit if requested
            if self._auto_quit:
                from PyQt6.QtWidgets import QApplication
                import json
                
                logger.info("Auto-quit requested, closing application")
                # Delay to allow GUI updates to complete, then export and quit
                def export_and_quit():
                    self._export_plot_data()
                    QTimer.singleShot(500, QApplication.quit)
                
                QTimer.singleShot(500, export_and_quit)

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

    def _export_plot_data(self) -> None:
        """
        Export plot data from all probe panels for test verification.

        Outputs JSON lines to stderr in format:
        PLOT_DATA:{"symbol": "x", "y": [9, 8, 7]}

        For constellation data (complex arrays):
        PLOT_DATA:{"symbol": "x", "real": [...], "imag": [...], "mean_real": 0.1, "mean_imag": -0.2}

        For waveform with overlays (list of curve dicts):
        PLOT_DATA:{"symbol": "x", "curves": [{"name": "x", "y": [...], "is_overlay": false}, ...]}
        """
        import json
        import numpy as np

        class NumpyEncoder(json.JSONEncoder):
            """JSON encoder that handles numpy types."""
            def default(self, obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                if isinstance(obj, np.floating):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super().default(obj)

        for anchor, panel_list in self._probe_panels.items():
            for panel in panel_list:
                plot_data = panel.get_plot_data()
                export_record = {
                    'symbol': anchor.symbol,
                    'line': anchor.line,
                    'col': anchor.col,
                    'is_assignment': anchor.is_assignment,
                }
                # Handle list-of-dicts format (waveform with potential overlays)
                if isinstance(plot_data, list) and plot_data:
                    # Check if any curve has overlay data
                    has_overlays = any(d.get('is_overlay', False) for d in plot_data if isinstance(d, dict))
                    if has_overlays:
                        # Export full curve list including overlays
                        export_record['curves'] = plot_data
                    else:
                        # Legacy: export first curve y values
                        first = plot_data[0] if plot_data else {}
                        if 'y' in first:
                            export_record['y'] = first['y']
                elif isinstance(plot_data, dict):
                    # Include standard y values if present
                    if 'y' in plot_data:
                        export_record['y'] = plot_data.get('y', [])
                    # Include constellation data if present (real/imag pairs)
                    if 'real' in plot_data and 'imag' in plot_data:
                        export_record['real'] = plot_data['real']
                        export_record['imag'] = plot_data['imag']
                        export_record['mean_real'] = plot_data.get('mean_real', 0.0)
                        export_record['mean_imag'] = plot_data.get('mean_imag', 0.0)
                        export_record['history_count'] = plot_data.get('history_count', 0)
                print(f"PLOT_DATA:{json.dumps(export_record, cls=NumpyEncoder)}", file=sys.stderr)

    # === M2.5: Park / Restore / Overlay ===

    def _on_panel_park_requested(self, anchor: ProbeAnchor) -> None:
        """Park all panels for an anchor to the dock bar."""
        if anchor not in self._probe_panels:
            return

        # Hide all panels for this anchor
        for panel in self._probe_panels[anchor]:
            panel.hide()

        # Mark panels as parked and relayout remaining panels
        self._probe_container.park_panel(anchor)

        # Add to dock bar
        anchor_key = anchor.identity_label()
        color = self._probe_registry.get_color(anchor)
        self._dock_bar.add_panel(anchor_key, anchor.symbol, color or QColor('#00ffff'))
        self._dock_bar.setVisible(True)

        logger.debug(f"Panel parked: {anchor_key}")
        self._status_bar.showMessage(f"Parked: {anchor.symbol}")

    def _on_dock_bar_restore(self, anchor_key: str) -> None:
        """Restore panels from the dock bar."""
        # Find panels matching this anchor_key
        for anchor, panel_list in self._probe_panels.items():
            if anchor.identity_label() == anchor_key:
                for panel in panel_list:
                    panel.show()
                self._dock_bar.remove_panel(anchor_key)
                # Unpark and relayout all panels including restored ones
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
