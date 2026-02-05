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
    run_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
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

        # Run button
        self._run_btn = QToolButton()
        self._run_btn.setText("Run")
        self._run_btn.setObjectName("runButton")
        self._run_btn.setToolTip("Run script (F5)")
        self._run_btn.setEnabled(False)
        self._run_btn.clicked.connect(self.run_clicked.emit)
        self.addWidget(self._run_btn)

        # Pause button
        self._pause_btn = QToolButton()
        self._pause_btn.setText("Pause")
        self._pause_btn.setObjectName("pauseButton")
        self._pause_btn.setToolTip("Pause/Resume execution (F6)")
        self._pause_btn.setEnabled(False)
        self._pause_btn.clicked.connect(self._on_pause_clicked)
        self.addWidget(self._pause_btn)

        # Stop button
        self._stop_btn = QToolButton()
        self._stop_btn.setText("Stop")
        self._stop_btn.setObjectName("stopButton")
        self._stop_btn.setToolTip("Stop execution (Shift+F5)")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self.stop_clicked.emit)
        self.addWidget(self._stop_btn)

        self.addSeparator()

        # Script path label
        self._script_label = QLabel("No script loaded")
        self._script_label.setStyleSheet("color: #888888; padding: 0 8px;")
        self.addWidget(self._script_label)

    def _on_pause_clicked(self):
        """Handle pause button click."""
        self._is_paused = not self._is_paused
        self._pause_btn.setText("Resume" if self._is_paused else "Pause")
        self.pause_clicked.emit()

    @property
    def is_paused(self) -> bool:
        """Check if currently paused."""
        return self._is_paused

    def set_script_loaded(self, loaded: bool, path: str = ""):
        """Update UI when script is loaded/unloaded."""
        self._script_loaded = loaded
        self._run_btn.setEnabled(loaded and not self._is_running)

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

        self._run_btn.setEnabled(self._script_loaded and not running)
        self._pause_btn.setEnabled(running)
        self._pause_btn.setText("Pause")
        self._stop_btn.setEnabled(running)
        self._open_btn.setEnabled(not running)
