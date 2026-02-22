"""
Dark cyberpunk theme for PyProbe.
Inspired by dark themes with neon accents.
"""

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QPalette, QColor, QFont

from .base import Theme


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

    # Semantic aliases (same values as neon_*, used by theme-aware widgets)
    'accent_primary': '#00ffff',
    'accent_secondary': '#ff00ff',
    'accent_marker': '#ffff00',
    'success': '#00ff00',
    'warning': '#ffff00',
    'error': '#ff0044',
    'border_default': '#333333',
    'border_strong': '#444444',
}


def _build_stylesheet(c: dict) -> str:
    """Build the QSS stylesheet from a colors dict."""
    return f"""
/* Main Window */
QMainWindow {{
    background-color: {c['bg_darkest']};
}}

/* Central Widget */
QWidget {{
    background-color: {c['bg_dark']};
    color: {c['text_primary']};
    font-family: "Menlo", "Consolas", "Monaco", monospace;
    font-size: 11px;
}}

/* Tool Bar */
QToolBar {{
    background-color: {c['bg_darkest']};
    border-bottom: 1px solid {c['accent_primary']};
    padding: 4px;
    spacing: 8px;
}}

QToolBar QToolButton {{
    background-color: {c['bg_medium']};
    border: 1px solid {c['border_default']};
    border-radius: 4px;
    padding: 6px 12px;
    color: {c['text_primary']};
    font-weight: bold;
}}

QToolBar QToolButton:hover {{
    background-color: {c['bg_light']};
    border-color: {c['accent_primary']};
    color: {c['accent_primary']};
}}

QToolBar QToolButton:pressed {{
    background-color: {c['bg_darkest']};
    border-color: {c['accent_secondary']};
}}

QToolBar QToolButton:disabled {{
    color: {c['text_muted']};
    border-color: {c['border_dark']};
}}

/* Status Bar */
QStatusBar {{
    background-color: {c['bg_darkest']};
    border-top: 1px solid {c['border_default']};
    color: {c['accent_primary']};
    font-size: 11px;
}}

/* Splitter */
QSplitter::handle {{
    background-color: {c['border_default']};
}}

QSplitter::handle:hover {{
    background-color: {c['accent_primary']};
}}

/* List Widget (Watch List) */
QListWidget {{
    background-color: {c['bg_darkest']};
    border: 1px solid {c['border_default']};
    border-radius: 4px;
    padding: 4px;
}}

QListWidget::item {{
    background-color: {c['bg_medium']};
    border: 1px solid {c['border_dark']};
    border-radius: 3px;
    padding: 8px;
    margin: 2px 0px;
}}

QListWidget::item:selected {{
    background-color: {c['bg_light']};
    border-color: {c['accent_primary']};
}}

QListWidget::item:hover {{
    border-color: {c['accent_secondary']};
}}

/* Line Edit */
QLineEdit {{
    background-color: {c['bg_medium']};
    border: 1px solid {c['border_default']};
    border-radius: 4px;
    padding: 6px;
    color: {c['text_primary']};
    selection-background-color: {c['accent_primary']};
    selection-color: {c['bg_darkest']};
}}

QLineEdit:focus {{
    border-color: {c['accent_primary']};
}}

QLineEdit::placeholder {{
    color: {c['text_muted']};
}}

/* Push Button */
QPushButton {{
    background-color: {c['bg_medium']};
    border: 1px solid {c['accent_primary']};
    border-radius: 4px;
    padding: 8px 16px;
    color: {c['accent_primary']};
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: rgba(0, 255, 255, 0.1);
}}

QPushButton:pressed {{
    background-color: rgba(0, 255, 255, 0.2);
}}

QPushButton:disabled {{
    border-color: {c['text_muted']};
    color: {c['text_muted']};
}}

/* Run Button (special green) */
QPushButton#runButton {{
    border-color: {c['success']};
    color: {c['success']};
}}

QPushButton#runButton:hover {{
    background-color: rgba(0, 255, 0, 0.1);
}}

/* Stop Button (special red) */
QPushButton#stopButton {{
    border-color: {c['error']};
    color: {c['error']};
}}

QPushButton#stopButton:hover {{
    background-color: rgba(255, 0, 68, 0.1);
}}

/* Pause Button (special yellow) */
QPushButton#pauseButton {{
    border-color: {c['warning']};
    color: {c['warning']};
}}

QPushButton#pauseButton:hover {{
    background-color: rgba(255, 255, 0, 0.1);
}}

/* Scroll Bar */
QScrollBar:vertical {{
    background-color: {c['bg_darkest']};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {c['border_default']};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {c['accent_primary']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {c['bg_darkest']};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {c['border_default']};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {c['accent_primary']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Group Box (Probe Panels) */
QGroupBox {{
    background-color: {c['bg_dark']};
    border: 1px solid {c['border_default']};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
}}

QGroupBox::title {{
    color: {c['accent_primary']};
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    font-weight: bold;
}}

/* Label */
QLabel {{
    background-color: transparent;
}}

/* Frame */
QFrame {{
    border: none;
}}

/* Flow Layout Container */
QScrollArea {{
    border: none;
    background-color: {c['bg_dark']};
}}

/* Message Box */
QMessageBox {{
    background-color: {c['bg_dark']};
}}

QMessageBox QLabel {{
    color: {c['text_primary']};
}}

/* Tooltip */
QToolTip {{
    background-color: {c['bg_medium']};
    border: 1px solid {c['accent_primary']};
    color: {c['text_primary']};
    padding: 4px 8px;
    border-radius: 4px;
}}
"""


STYLESHEET = _build_stylesheet(COLORS)


SYNTAX_COLORS = {
    'keyword': COLORS['neon_cyan'],
    'string': COLORS['neon_green'],
    'comment': COLORS['text_muted'],
    'number': COLORS['neon_yellow'],
    'function': COLORS['neon_magenta'],
    'class': COLORS['neon_orange'],
    'decorator': COLORS['neon_cyan'],
}

PLOT_COLORS = {
    'bg': COLORS['bg_darkest'],
    'grid_major': COLORS['border_medium'],
    'grid_minor': COLORS['border_dark'],
    'grid_alpha': 0.60,
    'grid_origin_alpha': 0.68,
    'axis': COLORS['text_secondary'],
    'marker': COLORS['neon_yellow'],
    'selection': COLORS['neon_cyan'],
    'success': COLORS['neon_green'],
    'error': COLORS['neon_red'],
}

ROW_COLORS = [
    '#00ffff', '#ff00ff', '#00ff00', '#ffff00', '#ff8800',
    '#00aaff', '#ff44aa', '#88ff00', '#ffaa00', '#aa00ff',
]

CYBERPUNK_THEME = Theme(
    name='Cyberpunk',
    id='cyberpunk',
    colors=COLORS,
    stylesheet=STYLESHEET,
    syntax_colors=SYNTAX_COLORS,
    plot_colors=PLOT_COLORS,
    row_colors=ROW_COLORS,
)


def _apply_font_and_palette(app: QApplication) -> None:
    """Apply legacy font + palette behavior for compatibility."""
    font = QFont()
    font.setFamilies(["Menlo", "Consolas", "Monaco", "monospace"])
    font.setPointSize(10)
    font.setStyleHint(QFont.StyleHint.Monospace)
    app.setFont(font)

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


def apply_cyberpunk_theme(widget: QWidget) -> None:
    """Backward-compatible shim: apply cyberpunk theme globally."""
    del widget  # Theme now applies application-wide.
    app = QApplication.instance()
    if app is None:
        return

    from .theme_manager import ThemeManager

    ThemeManager.instance(app).set_theme(CYBERPUNK_THEME.id)
    _apply_font_and_palette(app)
