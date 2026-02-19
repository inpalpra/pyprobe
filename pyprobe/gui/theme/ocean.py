"""Ocean dark theme for PyProbe."""

from .base import Theme


COLORS = {
    'bg_darkest': '#061622',
    'bg_dark': '#0b1f2f',
    'bg_medium': '#132b40',
    'bg_light': '#1b3954',

    'border_dark': '#1e3a52',
    'border_medium': '#295071',
    'border_light': '#35658f',

    'neon_cyan': '#4fd1ff',
    'neon_magenta': '#b38bff',
    'neon_green': '#2de2a1',
    'neon_yellow': '#ffd166',
    'neon_red': '#ff6b6b',
    'neon_orange': '#ff9f43',

    'text_primary': '#e8f3ff',
    'text_secondary': '#b9d0e6',
    'text_muted': '#7f9db8',

    'accent_primary': '#4fd1ff',
    'accent_secondary': '#2de2a1',
    'accent_marker': '#ffd166',
    'success': '#2de2a1',
    'warning': '#ff9f43',
    'error': '#ff6b6b',
    'border_default': '#295071',
    'border_strong': '#35658f',
}


def _build_stylesheet(c: dict) -> str:
    return f"""
QMainWindow {{
    background-color: {c['bg_darkest']};
}}

QWidget {{
    background-color: {c['bg_dark']};
    color: {c['text_primary']};
    font-family: \"Inter\", \"SF Pro Text\", \"Segoe UI\", \"Noto Sans\", sans-serif;
    font-size: 12px;
}}

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
    font-weight: 600;
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

QStatusBar {{
    background-color: {c['bg_darkest']};
    border-top: 1px solid {c['border_default']};
    color: {c['accent_primary']};
    font-size: 11px;
}}

QSplitter::handle {{
    background-color: {c['border_default']};
}}

QSplitter::handle:hover {{
    background-color: {c['accent_primary']};
}}

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

QPushButton {{
    background-color: {c['bg_medium']};
    border: 1px solid {c['accent_primary']};
    border-radius: 4px;
    padding: 8px 16px;
    color: {c['accent_primary']};
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: rgba(79, 209, 255, 0.12);
}}

QPushButton:pressed {{
    background-color: rgba(79, 209, 255, 0.22);
}}

QPushButton:disabled {{
    border-color: {c['text_muted']};
    color: {c['text_muted']};
}}

QPushButton#runButton {{
    border-color: {c['success']};
    color: {c['success']};
}}

QPushButton#runButton:hover {{
    background-color: rgba(45, 226, 161, 0.12);
}}

QPushButton#stopButton {{
    border-color: {c['error']};
    color: {c['error']};
}}

QPushButton#stopButton:hover {{
    background-color: rgba(255, 107, 107, 0.12);
}}

QPushButton#pauseButton {{
    border-color: {c['warning']};
    color: {c['warning']};
}}

QPushButton#pauseButton:hover {{
    background-color: rgba(255, 159, 67, 0.12);
}}

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
    font-weight: 600;
}}

QLabel {{
    background-color: transparent;
}}

QFrame {{
    border: none;
}}

QScrollArea {{
    border: none;
    background-color: {c['bg_dark']};
}}

QMessageBox {{
    background-color: {c['bg_dark']};
}}

QMessageBox QLabel {{
    color: {c['text_primary']};
}}

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
    'keyword': '#67b7ff',
    'string': '#52d6a3',
    'comment': '#7f9db8',
    'number': '#ffd166',
    'function': '#4fd1ff',
    'class': '#9ecbff',
    'decorator': '#ff9f43',
}

PLOT_COLORS = {
    'bg': '#061622',
    'grid_major': '#295071',
    'grid_minor': '#1e3a52',
    'grid_alpha': 0.24,
    'grid_origin_alpha': 0.32,
    'axis': '#b9d0e6',
    'marker': '#ffd166',
    'selection': '#4fd1ff',
    'success': '#2de2a1',
    'error': '#ff6b6b',
}

ROW_COLORS = [
    '#4fd1ff', '#2de2a1', '#ffd166', '#b38bff', '#ff9f43',
    '#7be0ff', '#75f0bf', '#ffe18e', '#d3b7ff', '#ffb972',
]

OCEAN_THEME = Theme(
    name='Ocean Dark',
    id='ocean',
    colors=COLORS,
    stylesheet=STYLESHEET,
    syntax_colors=SYNTAX_COLORS,
    plot_colors=PLOT_COLORS,
    row_colors=ROW_COLORS,
)
