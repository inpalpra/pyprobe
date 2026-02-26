"""
Control bar with Run/Pause/Stop buttons and script selection.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QToolBar, QToolButton, QWidget, QLabel, QHBoxLayout, QMenu
)
from PyQt6.QtCore import pyqtSignal, QTimer


class ControlBar(QToolBar):
    """
    Toolbar with playback controls for script execution.
    """

    # Signals
    open_clicked = pyqtSignal()
    open_folder_clicked = pyqtSignal()
    action_clicked = pyqtSignal()
    action_clicked_with_state = pyqtSignal(str)  # "Run" | "Pause" | "Resume"
    stop_clicked = pyqtSignal()
    loop_toggled = pyqtSignal(bool)  # checked

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._script_loaded = False
        self._is_running = False
        self._is_paused = False
        
        # Animation state
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(50)  # 20 FPS
        self._pulse_timer.timeout.connect(self._update_pulse)
        self._pulse_value = 0.0
        self._pulse_direction = 1

        self._setup_ui()

    def _setup_ui(self):
        """Create the toolbar UI."""
        self.setMovable(False)

        # Open button with dropdown menu
        self._open_btn = QToolButton()
        self._open_btn.setText("Open")
        self._open_btn.setToolTip("Open file or folder")
        self._open_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        open_menu = QMenu(self._open_btn)
        open_file_action = open_menu.addAction("Open File...\tCtrl+O")
        open_folder_action = open_menu.addAction("Open Folder...\tCtrl+Shift+O")
        open_file_action.triggered.connect(self.open_clicked.emit)
        open_folder_action.triggered.connect(self.open_folder_clicked.emit)
        self._open_btn.setMenu(open_menu)
        self.addWidget(self._open_btn)

        self.addSeparator()

        # Action button (Run/Pause/Resume)
        self._action_btn = QToolButton()
        self._action_btn.setText("Run")
        self._action_btn.setObjectName("runButton")
        self._action_btn.setToolTip("Run script (F5)")
        self._action_btn.setEnabled(False)
        self._action_btn.clicked.connect(self._on_action_clicked)
        self.addWidget(self._action_btn)

        # Stop button
        self._stop_btn = QToolButton()
        self._stop_btn.setText("Stop")
        self._stop_btn.setObjectName("stopButton")
        self._stop_btn.setToolTip("Stop execution (Shift+F5)")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self.stop_clicked.emit)
        self.addWidget(self._stop_btn)

        self.addSeparator()

        # Loop button
        self._loop_btn = QToolButton()
        self._loop_btn.setText("Loop")
        self._loop_btn.setCheckable(True)
        self._loop_btn.setObjectName("loopButton")
        self._loop_btn.setToolTip("Run script continuously (Loop)")
        self._loop_btn.setEnabled(False)
        self._loop_btn.toggled.connect(self._on_loop_toggled)
        self.addWidget(self._loop_btn)

        self.addSeparator()

        # Script path label
        self._script_label = QLabel("No script loaded")
        self.addWidget(self._script_label)

        # Connect to theme
        from .theme.theme_manager import ThemeManager
        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.current)

    @property
    def is_paused(self) -> bool:
        """Check if currently paused."""
        return self._is_paused

    @property
    def is_loop_enabled(self) -> bool:
        """Check if loop mode is enabled."""
        return self._loop_btn.isChecked()

    def set_script_loaded(self, loaded: bool, path: str = ""):
        """Update UI when script is loaded/unloaded."""
        self._script_loaded = loaded
        self._action_btn.setEnabled(loaded)
        self._loop_btn.setEnabled(loaded)

        # Reset state if unloaded
        if not loaded:
            self._is_running = False
            self._is_paused = False
            self._update_action_button()

        if loaded and path:
            # Show just the filename
            import os
            filename = os.path.basename(path)
            self._script_label.setText(filename)
            self._script_label.setToolTip(path)
        else:
            self._script_label.setText("No script loaded")
            self._script_label.setToolTip("")

    def set_running(self, running: bool):
        """Update UI when script starts/stops running."""
        self._is_running = running
        self._is_paused = False

        self._stop_btn.setEnabled(running)
        self._open_btn.setEnabled(not running)
        self._update_action_button()

    def set_paused(self, paused: bool):
        """Update UI when script is paused/resumed."""
        self._is_paused = paused
        self._update_action_button()

    def _update_action_button(self):
        """Update action button text/icon based on state."""
        if not self._is_running:
            self._action_btn.setText("Run")
            self._action_btn.setToolTip("Run script (F5)")
        elif self._is_paused:
            self._action_btn.setText("Resume")
            self._action_btn.setToolTip("Resume execution (F5)")
        else:
            self._action_btn.setText("Pause")
            self._action_btn.setToolTip("Pause execution (F5)")

    def _on_action_clicked(self):
        """Emit both generic and state-aware action signals."""
        self.action_clicked.emit()
        state = self._action_btn.text()  # "Run", "Pause", or "Resume"
        self.action_clicked_with_state.emit(state)

    def _on_loop_toggled(self, checked: bool):
        """Handle loop button toggle."""
        self.loop_toggled.emit(checked)
        if checked:
            self._pulse_value = 0.0
            self._pulse_direction = 1
            self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
            # Reset style to default (handled by stylesheets if empty string)
            # Typically removing inline style reverts to qss file
            self._loop_btn.setStyleSheet("")

    def _update_pulse(self):
        """Update the pulse animation."""
        step = 0.05
        if self._pulse_direction == 1:
            self._pulse_value += step
            if self._pulse_value >= 1.0:
                self._pulse_value = 1.0
                self._pulse_direction = -1
        else:
            self._pulse_value -= step
            if self._pulse_value <= 0.0:
                self._pulse_value = 0.0
                self._pulse_direction = 1
        
        # User requested: "glow from dark green to bright green"
        # We'll interpolate Green channel from ~100 to 255.
        min_g = 100
        max_g = 255
        current_g = int(min_g + (max_g - min_g) * self._pulse_value)
        
        # Create hex color #00GG00
        color_hex = f"#00{current_g:02x}00"
        
        # Also vary background alpha slightly for "glow" feel
        min_alpha = 0.05
        max_alpha = 0.20
        current_alpha = min_alpha + (max_alpha - min_alpha) * self._pulse_value
        
        # Apply stylesheet
        # Note: We target QToolButton by object name to ensure specificity if needed, 
        # but inline style overrides external stylesheet usually.
        self._loop_btn.setStyleSheet(f"""
            QToolButton {{
                color: {color_hex};
                border: 1px solid {color_hex};
                background-color: rgba(0, {current_g}, 0, {current_alpha:.2f});
            }}
        """)

    def _apply_theme(self, theme) -> None:
        c = theme.colors
        self._script_label.setStyleSheet(
            f"color: {c['text_secondary']}; padding: 0 8px;"
        )
