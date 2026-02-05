"""
Application entry point and setup.
"""

import sys
from typing import List, Optional
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

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


def run_app(script_path: str = None, watch_variables: Optional[List[str]] = None) -> int:
    """Run the PyProbe application."""
    app = create_app()

    window = MainWindow(script_path=script_path, watch_variables=watch_variables)
    window.show()

    return app.exec()
