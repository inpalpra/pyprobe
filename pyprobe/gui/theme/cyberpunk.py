"""
Dark cyberpunk theme for PyProbe.
Inspired by LabVIEW's dark theme with neon accents.
"""

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtCore import Qt


# Color Palette
COLORS = {
    # Backgrounds
    'bg_darkest': '#0a0a0a',      # Main background
    'bg_dark': '#0d0d0d',          # Panel background
    'bg_medium': '#1a1a1a',        # Widget background
    'bg_light': '#2a2a2a',         # Hover background

    # Borders
    'border_dark': '#1f1f1f',
    'border_medium': '#333333',
    'border_light': '#444444',

    # Neon accents
    'neon_cyan': '#00ffff',        # Primary accent (cyan)
    'neon_magenta': '#ff00ff',     # Secondary accent (magenta)
    'neon_green': '#00ff00',       # Success/data (green)
    'neon_yellow': '#ffff00',      # Warning (yellow)
    'neon_red': '#ff0044',         # Error/stop (red)
    'neon_orange': '#ff8800',      # Alert (orange)

    # Text
    'text_primary': '#ffffff',
    'text_secondary': '#aaaaaa',
    'text_muted': '#666666',
}


STYLESHEET = """
/* Main Window */
QMainWindow {
    background-color: #0a0a0a;
}

/* Central Widget */
QWidget {
    background-color: #0d0d0d;
    color: #ffffff;
    font-family: "Menlo", "Consolas", "Monaco", monospace;
    font-size: 11px;
}

/* Tool Bar */
QToolBar {
    background-color: #0a0a0a;
    border-bottom: 1px solid #00ffff;
    padding: 4px;
    spacing: 8px;
}

QToolBar QToolButton {
    background-color: #1a1a1a;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 6px 12px;
    color: #ffffff;
    font-weight: bold;
}

QToolBar QToolButton:hover {
    background-color: #2a2a2a;
    border-color: #00ffff;
    color: #00ffff;
}

QToolBar QToolButton:pressed {
    background-color: #0a0a0a;
    border-color: #ff00ff;
}

QToolBar QToolButton:disabled {
    color: #666666;
    border-color: #1f1f1f;
}

/* Status Bar */
QStatusBar {
    background-color: #0a0a0a;
    border-top: 1px solid #333333;
    color: #00ffff;
    font-size: 11px;
}

/* Splitter */
QSplitter::handle {
    background-color: #333333;
}

QSplitter::handle:hover {
    background-color: #00ffff;
}

/* List Widget (Watch List) */
QListWidget {
    background-color: #0a0a0a;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 4px;
}

QListWidget::item {
    background-color: #1a1a1a;
    border: 1px solid #1f1f1f;
    border-radius: 3px;
    padding: 8px;
    margin: 2px 0px;
}

QListWidget::item:selected {
    background-color: #2a2a2a;
    border-color: #00ffff;
}

QListWidget::item:hover {
    border-color: #ff00ff;
}

/* Line Edit */
QLineEdit {
    background-color: #1a1a1a;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 6px;
    color: #ffffff;
    selection-background-color: #00ffff;
    selection-color: #0a0a0a;
}

QLineEdit:focus {
    border-color: #00ffff;
}

QLineEdit::placeholder {
    color: #666666;
}

/* Push Button */
QPushButton {
    background-color: #1a1a1a;
    border: 1px solid #00ffff;
    border-radius: 4px;
    padding: 8px 16px;
    color: #00ffff;
    font-weight: bold;
}

QPushButton:hover {
    background-color: rgba(0, 255, 255, 0.1);
}

QPushButton:pressed {
    background-color: rgba(0, 255, 255, 0.2);
}

QPushButton:disabled {
    border-color: #666666;
    color: #666666;
}

/* Run Button (special green) */
QPushButton#runButton {
    border-color: #00ff00;
    color: #00ff00;
}

QPushButton#runButton:hover {
    background-color: rgba(0, 255, 0, 0.1);
}

/* Stop Button (special red) */
QPushButton#stopButton {
    border-color: #ff0044;
    color: #ff0044;
}

QPushButton#stopButton:hover {
    background-color: rgba(255, 0, 68, 0.1);
}

/* Pause Button (special yellow) */
QPushButton#pauseButton {
    border-color: #ffff00;
    color: #ffff00;
}

QPushButton#pauseButton:hover {
    background-color: rgba(255, 255, 0, 0.1);
}

/* Scroll Bar */
QScrollBar:vertical {
    background-color: #0a0a0a;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #333333;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #00ffff;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #0a0a0a;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: #333333;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #00ffff;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Group Box (Probe Panels) */
QGroupBox {
    background-color: #0d0d0d;
    border: 1px solid #333333;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
}

QGroupBox::title {
    color: #00ffff;
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    font-weight: bold;
}

/* Label */
QLabel {
    background-color: transparent;
}

/* Frame */
QFrame {
    border: none;
}

/* Flow Layout Container */
QScrollArea {
    border: none;
    background-color: #0d0d0d;
}

/* Message Box */
QMessageBox {
    background-color: #0d0d0d;
}

QMessageBox QLabel {
    color: #ffffff;
}

/* Tooltip */
QToolTip {
    background-color: #1a1a1a;
    border: 1px solid #00ffff;
    color: #ffffff;
    padding: 4px 8px;
    border-radius: 4px;
}
"""


def apply_cyberpunk_theme(widget: QWidget) -> None:
    """Apply the cyberpunk theme to a widget and its children."""
    app = QApplication.instance()
    if app:
        app.setStyleSheet(STYLESHEET)

        # Set monospace font (use commonly available fonts)
        font = QFont()
        font.setFamilies(["Menlo", "Consolas", "Monaco", "monospace"])
        font.setPointSize(10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        app.setFont(font)

        # Set palette for fallback styling
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(COLORS['bg_dark']))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(COLORS['text_primary']))
        palette.setColor(QPalette.ColorRole.Base, QColor(COLORS['bg_medium']))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(COLORS['bg_light']))
        palette.setColor(QPalette.ColorRole.Text, QColor(COLORS['text_primary']))
        palette.setColor(QPalette.ColorRole.Button, QColor(COLORS['bg_medium']))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(COLORS['text_primary']))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(COLORS['neon_cyan']))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(COLORS['bg_darkest']))
        app.setPalette(palette)
