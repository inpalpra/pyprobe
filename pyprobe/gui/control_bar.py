"""
Control bar with Run/Pause/Stop buttons and script selection.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QToolBar, QToolButton, QWidget, QLabel, QHBoxLayout
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction


class ControlBar(QToolBar):
    """
    Toolbar with playback controls for script execution.
    """

    # Signals
    open_clicked = pyqtSignal()
    action_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._script_loaded = False
        self._is_running = False
        self._is_paused = False

        self._setup_ui()

    def _setup_ui(self):
        """Create the toolbar UI."""
        self.setMovable(False)

        # Open button
        self._open_btn = QToolButton()
        self._open_btn.setText("Open")
        self._open_btn.setToolTip("Open Python script (Ctrl+O)")
        self._open_btn.clicked.connect(self.open_clicked.emit)
        self.addWidget(self._open_btn)

        self.addSeparator()

        # Action button (Run/Pause/Resume)
        self._action_btn = QToolButton()
        self._action_btn.setText("Run")
        self._action_btn.setObjectName("runButton")
        self._action_btn.setToolTip("Run script (F5)")
        self._action_btn.setEnabled(False)
        self._action_btn.clicked.connect(self.action_clicked.emit)
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
        self.addWidget(self._loop_btn)

        self.addSeparator()

        # Script path label
        self._script_label = QLabel("No script loaded")
        self._script_label.setStyleSheet("color: #888888; padding: 0 8px;")
        self.addWidget(self._script_label)

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
