"""
Main application window with probe panels and controls.

M1: Source-anchored probing with code viewer.
"""

from typing import Dict, List, Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QStatusBar, QFileDialog, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QAction, QActionGroup
import multiprocessing as mp
import os
import sys
import numpy as np
from PyQt6 import sip

from pyprobe.logging import get_logger, trace_print
logger = get_logger(__name__)


def is_obj_deleted(obj):
    """Safely check if a Qt object has been deleted."""
    return obj is None or sip.isdeleted(obj)

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
from ..core.trace_reference_manager import TraceReferenceManager
from .scalar_watch_window import ScalarWatchSidebar
from .redraw_throttler import RedrawThrottler
from .file_tree import FileTreePanel
from .collapsible_pane import CollapsiblePane
from .equation_editor import EquationEditorDialog
from ..core.equation_manager import EquationManager
from ..report.step_recorder import StepRecorder


def _safe_anchor_label(panel) -> str:
    """Return the identity label for a panel's anchor, or 'unknown' if unavailable."""
    anchor = getattr(panel, 'anchor', None)
    return anchor.identity_label() if anchor else "unknown"


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
        
        try:
            import sys, os
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
            from examples.interaction_discovery_hook import inject_logger
            inject_logger()
        except Exception as e:
            print(f"Failed to inject logger: {e}", flush=True)

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
        self._report_bug_dialog = None  # ReportBugDialog | None
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
        self._pending_markers = {} # (line, symbol) -> markers_dict

        # M4: Equation Manager
        self._equation_manager = EquationManager()
        self._latest_trace_data = {}

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
            is_in_watch=lambda a: self._scalar_watch_sidebar.has_scalar(a),
            parent=self
        )
        self._setup_probe_controller()

        # Step recorder for bug reports — owned by MainWindow, injected into dialog
        self._step_recorder = StepRecorder()
        self._connect_step_recorder()

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

    def _anchor_in_use_anywhere(self, anchor: ProbeAnchor) -> bool:
        """Check if anchor is still in use in any panel, overlay, or watch sidebar."""
        if self._probe_controller.has_active_panels(anchor):
            return True
        if self._probe_controller.is_used_as_overlay(anchor):
            return True
        if self._scalar_watch_sidebar.has_scalar(anchor):
            return True
        return False

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
                self._on_probe_requested(anchor, lens_name=lens_str)
                
                # Apply stored markers if any
                panel_list = self._probe_controller.probe_panels.get(anchor, [])
                if panel_list and (anchor.line, anchor.symbol) in self._pending_markers:
                    panel = panel_list[-1]
                    markers_data = self._pending_markers[(anchor.line, anchor.symbol)]
                    if hasattr(panel, 'restore_marker_state'):
                        panel.restore_marker_state(markers_data)
                    
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
        self._probe_container.panel_closing.connect(self._on_panel_closing)
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

        # Right-aligned coordinate label for hover display
        self._coord_label = QLabel("")
        self._coord_label.setStyleSheet("color: #aaaaaa; font-family: 'JetBrains Mono'; font-size: 11px; padding-right: 8px;")
        self._status_bar.addPermanentWidget(self._coord_label)

        self._setup_theme_menu()
        self._setup_help_menu()

    def _setup_help_menu(self) -> None:
        help_menu = self.menuBar().addMenu("Help")
        report_action = help_menu.addAction("Report Bug")
        # Use a lambda so patch.object works in tests (re-resolves the method on each call).
        report_action.triggered.connect(lambda: self._show_report_bug_dialog())

    def _show_report_bug_dialog(self) -> None:
        from pyprobe.gui.report_bug_dialog import ReportBugDialog
        from pyprobe.report.session_snapshot import SessionStateCollector

        # Prevent duplicate dialogs — bring existing one to front.
        if self._report_bug_dialog is not None:
            self._report_bug_dialog.raise_()
            self._report_bug_dialog.activateWindow()
            return

        collector = SessionStateCollector(
            file_getter=lambda: self._code_viewer.open_file_entries(),
            probe_getter=lambda: self._probe_controller.probe_trace_entries(),
            equation_getter=lambda: self._equation_manager.equation_entries(),
            widget_getter=lambda: self._probe_container.graph_widget_entries(self._probe_registry),
        )
        dialog = ReportBugDialog(collector=collector, recorder=self._step_recorder, parent=self)
        dialog.finished.connect(self._on_report_bug_dialog_closed)
        self._report_bug_dialog = dialog
        dialog.show()

    def _on_report_bug_dialog_closed(self, _result: int = 0) -> None:
        self._report_bug_dialog = None

    def _connect_step_recorder(self) -> None:
        """Wire all domain signals to the step recorder.

        Connections are permanent — the recorder ignores calls when not
        recording (zero overhead).
        """
        r = self._step_recorder

        # ── Probe lifecycle ───────────────────────────────────────────────
        r.connect_signal(
            self._probe_controller.probe_added,
            lambda anchor, panel: f"Added probe: {anchor.identity_label()}")
        r.connect_signal(
            self._probe_controller.probe_removed,
            lambda anchor: f"Removed probe: {anchor.identity_label()}")

        # ── Overlay addition / removal ────────────────────────────────────
        r.connect_signal(
            self._probe_controller.overlay_requested,
            lambda target_panel, overlay_anchor:
                f"Overlaid {overlay_anchor.identity_label()} onto panel containing {_safe_anchor_label(target_panel)}")
        r.connect_signal(
            self._probe_controller.overlay_remove_requested,
            lambda target_panel, overlay_anchor:
                f"Removed overlay {overlay_anchor.identity_label()} from {_safe_anchor_label(target_panel)}")

        # ── Watch sidebar ─────────────────────────────────────────────────
        r.connect_signal(
            self._code_viewer.watch_probe_requested,
            lambda anchor: f"Added watch: {anchor.identity_label()}")
        r.connect_signal(
            self._scalar_watch_sidebar.scalar_removed,
            lambda anchor: f"Removed watch: {anchor.identity_label()}")

        # ── Panel management ──────────────────────────────────────────────
        r.connect_signal(
            self._probe_container.panel_closing,
            lambda panel: f"Panel closed: {_safe_anchor_label(panel)}")
        r.connect_signal(
            self._probe_controller.panel_park_requested,
            lambda anchor: f"Parked panel: {anchor.identity_label()}")
        r.connect_signal(
            self._probe_controller.panel_maximize_requested,
            lambda anchor: f"Maximized panel: {anchor.identity_label()}")
        r.connect_signal(
            self._dock_bar.panel_restore_requested,
            lambda anchor_key: f"Restored parked panel: {anchor_key}")

        # ── Highlight transitions ─────────────────────────────────────────
        r.connect_signal(
            self._code_viewer.highlight_changed,
            lambda anchor, is_highlighted:
                f"Code viewer highlight {'added for' if is_highlighted else 'removed for'} {anchor.identity_label()}")

        # ── Script execution ──────────────────────────────────────────────
        r.connect_signal(
            self._control_bar.action_clicked_with_state,
            lambda state: f"Clicked {state}")
        r.connect_signal(self._control_bar.stop_clicked, "Clicked Stop")
        r.connect_signal(self._message_handler.script_ended, "Script finished")
        r.connect_signal(
            self._message_handler.exception_raised,
            lambda payload: f"Exception raised: {payload.get('type', 'unknown')}")

        # ── Control bar: open / loop ──────────────────────────────────────
        r.connect_signal(
            self._control_bar.open_clicked,
            "Opened file dialog")
        r.connect_signal(
            self._control_bar.open_folder_clicked,
            "Opened folder dialog")
        r.connect_signal(
            self._control_bar.loop_toggled,
            lambda checked: f"Loop mode {'enabled' if checked else 'disabled'}")

        # ── Equation overlay ──────────────────────────────────────────────
        r.connect_signal(
            self._probe_controller.equation_overlay_requested,
            lambda target_panel, eq_id:
                f"Overlaid equation {eq_id} onto panel containing {_safe_anchor_label(target_panel)}")

        # ── Per-panel signals (forwarded via probe_controller) ────────────
        r.connect_signal(
            self._probe_controller.panel_lens_changed,
            lambda anchor, wid, name: f"Changed format on window {wid} to {name}")
        r.connect_signal(
            self._probe_controller.panel_color_changed,
            lambda anchor, color: f"Changed color of {anchor.identity_label()} to {color.name()}")
        r.connect_signal(
            self._probe_controller.panel_draw_mode_changed,
            lambda anchor, key, mode: f"Changed draw mode to '{mode}' for {key} on {anchor.identity_label()}")
        r.connect_signal(
            self._probe_controller.panel_markers_cleared,
            lambda anchor: f"Cleared all markers on {anchor.identity_label()}")
        r.connect_signal(
            self._probe_controller.panel_trace_visibility_changed,
            lambda anchor, wid, name, visible: f"Toggled visibility of {name} in window {wid} ({anchor.identity_label()})")
        r.connect_signal(
            self._probe_controller.panel_legend_moved,
            lambda anchor, wid: f"Moved legend in window {wid} ({anchor.identity_label()})")
        r.connect_signal(
            self._probe_controller.panel_interaction_mode_changed,
            lambda anchor, wid, mode: f"Changed tool to {mode} in window {wid} ({anchor.identity_label()})")
        r.connect_signal(
            self._probe_controller.panel_view_reset_triggered,
            lambda anchor, wid: f"Reset view in window {wid} ({anchor.identity_label()})")
        r.connect_signal(
            self._probe_controller.panel_view_adjusted,
            lambda anchor, wid: f"Adjusted view in window {wid} ({anchor.identity_label()})")
        r.connect_signal(
            self._probe_controller.panel_view_interaction_triggered,
            lambda anchor, wid, desc: f"{desc} in window {wid} ({anchor.identity_label()})")

        # ── File tree ─────────────────────────────────────────────────────
        r.connect_signal(
            self._file_tree.file_selected,
            lambda path: f"Selected file: {path}")

        # ── Theme changes ─────────────────────────────────────────────────
        from .theme.theme_manager import ThemeManager
        r.connect_signal(
            ThemeManager.instance().theme_changed,
            lambda theme: f"Changed theme to '{theme.name}'")

    def _setup_theme_menu(self) -> None:
        """Create View -> Theme menu and wire runtime switching."""
        view_menu = self.menuBar().addMenu("View")
        
        # M4: Equation Editor
        eq_action = view_menu.addAction("Equation Editor")
        eq_action.triggered.connect(self._show_equation_editor)
        view_menu.addSeparator()

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

    def _show_equation_editor(self):
        """Show the equation editor dialog."""
        dialog = EquationEditorDialog.show_instance(self._equation_manager, self)
        dialog.plot_requested.connect(self._on_equation_plot_requested)
        self._connect_equation_editor_recorder(dialog)

    def _connect_equation_editor_recorder(self, dialog: EquationEditorDialog) -> None:
        """Wire equation editor signals to step recorder (idempotent)."""
        if getattr(dialog, '_recorder_connected', False):
            return
        dialog._recorder_connected = True
        r = self._step_recorder
        r.connect_signal(dialog.equation_added, lambda eq_id: f"Added equation: {eq_id}")
        r.connect_signal(dialog.equation_edited, lambda eq_id: f"Edited equation: {eq_id}")
        r.connect_signal(dialog.equation_deleted, lambda eq_id: f"Deleted equation: {eq_id}")
        r.connect_signal(dialog.plot_requested, lambda eq_id: f"Plotted equation: {eq_id}")

    def _on_equation_plot_requested(self, eq_id: str):
        """Handle 'Plot' click from Equation Editor."""
        # Create a new panel for the equation
        if not hasattr(self, "_equation_to_panels"):
            self._equation_to_panels = {}
            
        eq = self._equation_manager.equations.get(eq_id)
        if not eq:
            return
            
        # Check if we already have a panel for this equation
        if eq_id in self._equation_to_panels and self._equation_to_panels[eq_id]:
            # Just bring it to focus or show it if parked?
            # For now, let's just avoid creating a new one if one already exists.
            # We could potentially highlight it.
            self._status_bar.showMessage(f"Panel for {eq_id} already exists")
            return

        # Create a dummy anchor for the equation
        dummy_anchor = ProbeAnchor(file="<equation>", line=0, col=0, symbol=eq_id)
        
        # Determine dtype
        dtype = 'unknown'
        if eq.result is not None:
            dtype = 'array_1d' if not np.iscomplexobj(eq.result) else 'array_complex'
            
        # Add to registry (using a fake color)
        color = QColor('#00ffff')
        
        # For now, let's create the panel directly in the container
        panel = self._probe_container.create_panel(
            var_name=eq_id,
            dtype=dtype,
            anchor=dummy_anchor,
            color=color,
            trace_id=eq_id
        )
        
        if eq_id not in self._equation_to_panels:
            self._equation_to_panels[eq_id] = []
        self._equation_to_panels[eq_id].append(panel)
        
        # Trigger update if data available
        if eq.result is not None:
            self._update_equation_plots()

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

        # M3: Connect marker changes to save
        from ..plots.marker_model import MarkerStore
        MarkerStore.store_signals().marker_content_changed.connect(self._save_probe_settings)

        # Phase 5: Global unprobing integration
        TraceReferenceManager.instance().unprobe_signal.connect(self._on_unprobe_requested)

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
        print("[DIAG-PATH] _force_quit (timeout)", file=sys.stderr)
        logger.info("Auto-quit timeout reached, forcing application exit")
        self._force_redraw()
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
            anchor = record.anchor
            self._probe_registry.update_data_received(anchor)

            if anchor in self._probe_metadata:
                self._probe_metadata[anchor]['dtype'] = record.dtype
                self._probe_metadata[anchor]['shape'] = record.shape

            self._redraw_throttler.receive(record)

            if self._scalar_watch_sidebar.has_scalar(anchor):
                self._scalar_watch_sidebar.update_scalar(anchor, record.value)

            self._forward_overlay_data(anchor, {
                'value': record.value,
                'dtype': record.dtype,
                'shape': record.shape,
            })

            # Populate trace data for equations
            trace_id = self._probe_registry.get_trace_id(anchor)
            if trace_id:
                self._latest_trace_data[trace_id] = record.value

        # Evaluate equations if any exist
        if self._equation_manager.equations:
            self._equation_manager.evaluate_all(self._latest_trace_data)
            self._update_equation_plots()

        self._maybe_redraw()

    def _maybe_redraw(self) -> None:
        """Redraw dirty buffers at a throttled rate."""
        if not self._redraw_throttler.should_redraw():
            return

        dirty = self._redraw_throttler.get_dirty_buffers()
        for anchor, buffer in dirty.items():
            if anchor in self._probe_panels:
                for panel in self._probe_panels[anchor]:
                    if not is_obj_deleted(panel) and not panel.is_closing:
                        panel.update_from_buffer(buffer)
        
        # Flush any pending overlay data now that plot widgets may exist
        self._probe_controller.flush_pending_overlays()

    def _force_redraw(self) -> None:
        """Redraw all dirty buffers regardless of throttle."""
        dirty = self._redraw_throttler.get_dirty_buffers()
        for anchor, buffer in dirty.items():
            if anchor in self._probe_panels:
                for panel in self._probe_panels[anchor]:
                    if not is_obj_deleted(panel) and not panel.is_closing:
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
        self._probe_controller.status_message.connect(self._on_probe_status_message)
        
        # M2.5 & M4: Overlay signals
        self._probe_controller.overlay_requested.connect(self._on_overlay_requested)
        self._probe_controller.equation_overlay_requested.connect(self._on_equation_overlay_requested)
        self._probe_controller.overlay_remove_requested.connect(self._on_overlay_remove_requested)

    def _on_probe_status_message(self, msg: str):
        """Route coordinate messages to right-side label, others to status bar."""
        if msg.startswith("X:"):
            self._coord_label.setText(msg)
        elif msg == "":
            self._coord_label.setText("")
        else:
            self._status_bar.showMessage(msg)

    @pyqtSlot(dict)
    def _on_probe_value(self, payload: dict):
        """Handle single probe value from MessageHandler."""
        anchor = ProbeAnchor.from_dict(payload['anchor'])
        logger.debug(f"Received data for {anchor.symbol}")
        self._probe_registry.update_data_received(anchor)

        # Update all panels for this anchor
        if anchor in self._probe_panels:
            # Update metadata dtype
            if anchor in self._probe_metadata:
                self._probe_metadata[anchor]['dtype'] = payload['dtype']
                self._probe_metadata[anchor]['shape'] = payload.get('shape')

            for panel in self._probe_panels[anchor]:
                if not is_obj_deleted(panel) and not panel.is_closing:
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
            
            # Update trace data for equations
            trace_id = self._probe_registry.get_trace_id(anchor)
            if trace_id:
                self._latest_trace_data[trace_id] = probe_data['value']

            self._probe_registry.update_data_received(anchor)
            if anchor in self._probe_metadata:
                self._probe_metadata[anchor]['dtype'] = probe_data['dtype']
                self._probe_metadata[anchor]['shape'] = probe_data.get('shape')

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

        # M4: Evaluate equations
        if self._equation_manager.equations:
            self._equation_manager.evaluate_all(self._latest_trace_data)
            # Update any widgets currently plotting equations
            self._update_equation_plots()

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
                    if not is_obj_deleted(panel) and not panel.is_closing:
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
                    if not is_obj_deleted(panel) and not panel.is_closing:
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
        self._pending_markers = {}
        
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
            
            # Store markers for later restoration
            if p.markers:
                self._pending_markers[(p.line, p.symbol)] = p.markers
            
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
            
            # Extract color
            color_hex = None
            color = self._probe_registry.get_color(anchor)
            if color:
                color_hex = color.name()
                
            # Extract lens and markers from panels if available
            lens = None
            markers = None
            if hasattr(self, '_probe_controller'):
                # Check metadata for lens
                if anchor in self._probe_controller._probe_metadata:
                    metadata = self._probe_controller._probe_metadata[anchor]
                    if metadata.get('overlay_target') is not None:
                        continue
                    lens = metadata.get('lens')
                
                # Check panels for markers
                panel_list = [p for p in self._probe_controller._probe_panels.get(anchor, []) if not is_obj_deleted(p)]
                if panel_list:
                    panel = panel_list[-1]
                    if not getattr(panel, "is_closing", False) and hasattr(panel, 'get_marker_state'):
                        markers = panel.get_marker_state()
            
            spec = ProbeSpec.from_anchor(anchor, color=color_hex, lens=lens, markers=markers)
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
                # Filter out deleted panels
                valid_panels = [p for p in panel_list if not is_obj_deleted(p) and not getattr(p, "is_closing", False)]
                if not valid_panels:
                    continue
                target_panel = valid_panels[-1]
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
    def _on_probe_requested(self, anchor: ProbeAnchor, lens_name: Optional[str] = None):
        """Handle click-to-probe request from code viewer."""
        panel = self._probe_controller.add_probe(anchor, lens_name=lens_name)
        if panel:
            # Mark as graphical probe in code viewer
            self._code_viewer.set_probe_graphical(anchor)
            # M2.5: Connect park and overlay signals
            panel.park_requested.connect(lambda a=anchor: self._on_panel_park_requested(a))
            panel.overlay_requested.connect(self._on_overlay_requested)

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
        
        # Get Trace ID
        trace_id = self._probe_registry.get_trace_id(anchor)
        
        # Add to watch sidebar
        self._scalar_watch_sidebar.add_scalar(anchor, color, trace_id)
        
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
        # Always decrement highlight ref count for the watch's contribution
        self._code_viewer.remove_probe(anchor)

        # Only do global cleanup if not still used by panels or overlays
        still_has_panels = self._probe_controller.has_active_panels(anchor)
        still_as_overlay = self._probe_controller.is_used_as_overlay(anchor)

        if still_has_panels or still_as_overlay:
            logger.debug(
                f"Watch removed for {anchor.symbol} but still in use "
                f"(panels={still_has_panels}, overlay={still_as_overlay}), "
                f"skipping global cleanup"
            )
        else:
            # Only clear gutter if no other active probes on same line
            line_still_probed = any(
                a.line == anchor.line and a != anchor
                for a in self._probe_registry.active_anchors
            )
            if not line_still_probed:
                self._code_gutter.clear_probed_line(anchor.line)
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
                    if not is_obj_deleted(panel) and not panel.is_closing:
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
                if not is_obj_deleted(panel) and not panel.is_closing:
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
            self._control_bar.set_running(False)
            self._status_bar.showMessage("Ready")

            # Auto-quit if requested
            if self._auto_quit:
                from PyQt6.QtWidgets import QApplication
                import json
                
                logger.info("Auto-quit requested, closing application")
                # Delay to allow GUI updates to complete, then export, cleanup, and quit
                def export_and_quit():
                    self._export_plot_data()
                    self._script_runner.cleanup()
                    QTimer.singleShot(500, QApplication.quit)
                
                QTimer.singleShot(500, export_and_quit)
            else:
                self._script_runner.cleanup()

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
        if getattr(self, '_plot_data_exported', False):
            return
        self._plot_data_exported = True

        import json
        import numpy as np
        import sys

        # Ensure any pending throttled data is plotted before export
        self._force_redraw()

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
                if is_obj_deleted(panel) or panel.is_closing:
                    continue
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
            if not is_obj_deleted(panel) and not panel.is_closing:
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
                    if not is_obj_deleted(panel) and not panel.is_closing:
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

    def _on_equation_overlay_requested(self, target_panel: ProbePanel, eq_id: str) -> None:
        """Handle equation drop request."""
        if not hasattr(self, "_equation_to_panels"):
            self._equation_to_panels = {}
        
        if eq_id not in self._equation_to_panels:
            self._equation_to_panels[eq_id] = []
        
        if target_panel not in self._equation_to_panels[eq_id]:
            self._equation_to_panels[eq_id].append(target_panel)
            logger.info(f"Overlaid {eq_id} on panel {target_panel._anchor.symbol}")
            
            # Trigger update if data is available
            eq = self._equation_manager.equations.get(eq_id)
            if eq and eq.result is not None:
                self._update_equation_plots()

    def _update_equation_plots(self):
        """Update all panels that have equation overlays or are primary equation plots."""
        if not hasattr(self, "_equation_to_panels"):
            return
            
        from pyprobe.plugins.builtins.waveform import WaveformWidget
        from pyprobe.plugins.builtins.constellation import ConstellationWidget
        
        for eq_id, panels in self._equation_to_panels.items():
            eq = self._equation_manager.equations.get(eq_id)
            if not eq or eq.result is None:
                continue
                
            # Ensure result is a numpy array
            result = eq.result
            if not isinstance(result, np.ndarray):
                result = np.atleast_1d(result)
            
            dtype = 'array_1d' if not np.iscomplexobj(result) else 'array_complex'
                
            for panel in list(panels):
                # Check if panel still exists
                if sip.isdeleted(panel):
                    panels.remove(panel)
                    continue
                
                # If this is the primary panel for the equation, update it normally
                if panel._anchor.symbol == eq_id:
                    panel.update_data(result, dtype, result.shape)
                    continue
                    
                plot = panel._plot
                if plot is None:
                    continue
                
                # Treat equation result as an 'anchor' for overlay logic purposes
                # but with a special symbol eq_id
                dummy_anchor = ProbeAnchor(file="", line=0, col=0, symbol=eq_id)
                
                if isinstance(plot, WaveformWidget):
                    self._probe_controller._add_overlay_to_waveform(
                        plot, dummy_anchor, result, dtype, result.shape,
                        primary_anchor=panel._anchor,
                        target_panel=panel
                    )
                elif isinstance(plot, ConstellationWidget):
                    self._probe_controller._add_overlay_to_constellation(
                        plot, dummy_anchor, result, 'array_complex', result.shape,
                        primary_anchor=panel._anchor,
                        target_panel=panel
                    )

    def _forward_overlay_data(self, anchor: ProbeAnchor, payload: dict) -> None:
        """Forward overlay probe data - delegate to ProbeController."""
        self._probe_controller.forward_overlay_data(anchor, payload)

    def _on_overlay_remove_requested(self, target_panel: ProbePanel, overlay_anchor: ProbeAnchor) -> None:
        """Handle overlay removal request - delegate to ProbeController.

        Records the step BEFORE calling remove_overlay so it precedes
        the highlight_changed step that fires during handler execution.
        """
        target_label = _safe_anchor_label(target_panel)
        self._step_recorder.record(
            f"Removed overlay: {overlay_anchor.identity_label()} from panel containing {target_label}"
        )
        self._probe_controller.remove_overlay(target_panel, overlay_anchor)

    def _on_panel_closing(self, panel) -> None:
        """Clean up overlay highlights before a panel is removed."""
        self._probe_controller.handle_panel_closing(panel)

    @pyqtSlot(str)
    def _on_unprobe_requested(self, trace_id: str) -> None:
        """
        Handle a trace reaching zero references.
        Global cleanup of registry, code viewer, and runner.
        """
        print(f"DEBUG: MainWindow._on_unprobe_requested: {trace_id}", file=sys.stderr)
        
        if trace_id.startswith("tr"):
            anchor = self._probe_registry.get_anchor_by_trace_id(trace_id)
            print(f"DEBUG:   Found anchor: {anchor}", file=sys.stderr)
            if anchor:
                # Check if any non-deleted, non-closing panels remain for this anchor
                active_panels = [
                    p for p in self._probe_panels.get(anchor, []) 
                    if not is_obj_deleted(p) and not getattr(p, "is_closing", False)
                ]
                print(f"DEBUG:   Active panels: {len(active_panels)}", file=sys.stderr)
                
                if not active_panels:
                    # Always decrement highlight ref count for the panel's contribution
                    self._code_viewer.remove_probe(anchor)

                    # Check if anchor is still used as overlay or in watch sidebar
                    still_in_watch = self._scalar_watch_sidebar.has_scalar(anchor)
                    still_as_overlay = self._probe_controller.is_used_as_overlay(anchor)

                    if still_in_watch or still_as_overlay:
                        logger.debug(
                            f"Trace {trace_id} has no panels but still in use "
                            f"(watch={still_in_watch}, overlay={still_as_overlay}), "
                            f"skipping global cleanup"
                        )
                    else:
                        print(f"DEBUG:   Performing global cleanup for {anchor.symbol}", file=sys.stderr)
                        # Global cleanup (copy from controller.complete_probe_removal logic)
                        self._probe_registry.remove_probe(anchor)
                        # Only clear gutter if no other active probes on same line
                        line_still_probed = any(
                            a.line == anchor.line and a != anchor
                            for a in self._probe_registry.active_anchors
                        )
                        if not line_still_probed:
                            self._code_gutter.clear_probed_line(anchor.line)

                        # Remove from metadata if present
                        if anchor in self._probe_controller._probe_metadata:
                            del self._probe_controller._probe_metadata[anchor]

                        # Send to runner
                        ipc = self._script_runner.ipc
                        if ipc and self._script_runner.is_running:
                            msg = make_remove_probe_cmd(anchor)
                            ipc.send_command(msg)
                    
                    self._status_bar.showMessage(f"Probe removed globally: {anchor.symbol}", 3000)
                else:
                    logger.debug(f"Trace {trace_id} still has {len(active_panels)} active panels, skipping global cleanup")
                    
        elif trace_id.startswith("eq"):
            # Only clean up panel references — the equation itself persists
            # in the EquationManager until explicitly deleted via the editor
            if hasattr(self, "_equation_to_panels") and trace_id in self._equation_to_panels:
                del self._equation_to_panels[trace_id]
