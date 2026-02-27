"""Monokai-inspired dark theme for PyProbe."""

from .base import Theme


COLORS = {
    'bg_darkest': '#1f2024',
    'bg_dark': '#272822',
    'bg_medium': '#32332d',
    'bg_light': '#3d3e38',

    'border_dark': '#3a3b35',
    'border_medium': '#4a4b45',
    'border_light': '#5b5c55',

    'neon_cyan': '#66d9ef',
    'neon_magenta': '#f92672',
    'neon_green': '#a6e22e',
    'neon_yellow': '#e6db74',
    'neon_red': '#f44747',
    'neon_orange': '#fd971f',

    'text_primary': '#f8f8f2',
    'text_secondary': '#c6c6bf',
    'text_muted': '#8f908a',

    'accent_primary': '#66d9ef',
    'accent_secondary': '#f92672',
    'accent_marker': '#e6db74',
    'success': '#a6e22e',
    'warning': '#fd971f',
    'error': '#f44747',
    'border_default': '#4a4b45',
    'border_strong': '#5b5c55',
}


def _build_stylesheet(c: dict) -> str:
    return f"""
QMainWindow {{
    background-color: {c['bg_darkest']};
}}

QWidget {{
    background-color: {c['bg_dark']};
    color: {c['text_primary']};
    font-family: \"SF Mono\", \"JetBrains Mono\", \"Menlo\", \"Consolas\", \"Monaco\", monospace;
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
    background-color: rgba(102, 217, 239, 0.12);
}}

QPushButton:pressed {{
    background-color: rgba(102, 217, 239, 0.22);
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
    background-color: rgba(166, 226, 46, 0.12);
}}

QPushButton#stopButton {{
    border-color: {c['error']};
    color: {c['error']};
}}

QPushButton#stopButton:hover {{
    background-color: rgba(244, 71, 71, 0.12);
}}

QPushButton#pauseButton {{
    border-color: {c['warning']};
    color: {c['warning']};
}}

QPushButton#pauseButton:hover {{
    background-color: rgba(253, 151, 31, 0.12);
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
    'keyword': '#f92672',
    'string': '#e6db74',
    'comment': '#8f908a',
    'number': '#ae81ff',
    'function': '#a6e22e',
    'class': '#66d9ef',
    'decorator': '#fd971f',
}

PLOT_COLORS = {
    'bg': '#1f2024',
    'grid_major': '#4a4b45',
    'grid_minor': '#3a3b35',
    'grid_alpha': 0.56,
    'grid_origin_alpha': 0.64,
    'axis': '#c6c6bf',
    'marker': '#e6db74',
    'selection': '#66d9ef',
    'success': '#a6e22e',
    'error': '#f44747',
}

ROW_COLORS = [
    '#66d9ef', '#f92672', '#a6e22e', '#fd971f', '#ae81ff',
    '#e6db74', '#78dce8', '#ff6188', '#ffd866', '#a9dc76',
]

MONOKAI_THEME = Theme(
    name='Monokai Dark',
    id='monokai',
    colors=COLORS,
    stylesheet=STYLESHEET,
    syntax_colors=SYNTAX_COLORS,
    plot_colors=PLOT_COLORS,
    row_colors=ROW_COLORS,
)
