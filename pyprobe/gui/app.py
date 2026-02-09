"""
Application entry point and setup.
"""

import sys
from typing import List, Optional
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Configure PyQtGraph before importing any plot modules
import pyqtgraph as pg
pg.setConfigOptions(
    useOpenGL=False,           # Disable OpenGL to prevent rendering issues
    antialias=False,           # Disable antialiasing for performance
    enableExperimental=False,  # Disable experimental features
)

from .main_window import MainWindow


def create_app() -> QApplication:
    """Create and configure the QApplication."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("PyProbe")
    app.setOrganizationName("PyProbe")

    return app


def run_app(
    script_path: str = None,
    probes: Optional[List[str]] = None,
    watches: Optional[List[str]] = None,
    auto_run: bool = False,
    auto_quit: bool = False
) -> int:
    """Run the PyProbe application."""
    app = create_app()

    window = MainWindow(
        script_path=script_path,
        probes=probes,
        watches=watches,
        auto_run=auto_run,
        auto_quit=auto_quit
    )
    window.show()

    return app.exec()
