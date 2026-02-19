"""Anthropic-inspired dark theme for PyProbe."""

from .base import Theme


COLORS = {
    'bg_darkest': '#141413',
    'bg_dark': '#1b1b1a',
    'bg_medium': '#242422',
    'bg_light': '#2d2d2a',

    'border_dark': '#2e2e2b',
    'border_medium': '#3a3a36',
    'border_light': '#474742',

    'neon_cyan': '#7db1ff',
    'neon_magenta': '#a48bff',
    'neon_green': '#86c79d',
    'neon_yellow': '#e0ba7c',
    'neon_red': '#d98787',
    'neon_orange': '#d2a46f',

    'text_primary': '#f3f2ef',
    'text_secondary': '#cbc9c4',
    'text_muted': '#9a978f',

    'accent_primary': '#7db1ff',
    'accent_secondary': '#a48bff',
    'accent_marker': '#e0ba7c',
    'success': '#86c79d',
    'warning': '#d2a46f',
    'error': '#d98787',
    'border_default': '#3a3a36',
    'border_strong': '#474742',
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

QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    font-family: \"SF Mono\", \"JetBrains Mono\", \"Menlo\", \"Consolas\", \"Monaco\", monospace;
}}

QToolBar {{
    background-color: {c['bg_darkest']};
    border-bottom: 1px solid {c['border_default']};
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
    color: {c['text_secondary']};
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
    border-color: {c['border_strong']};
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
    border: 1px solid {c['border_strong']};
    border-radius: 4px;
    padding: 8px 16px;
    color: {c['text_primary']};
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: rgba(125, 177, 255, 0.10);
    border-color: {c['accent_primary']};
}}

QPushButton:pressed {{
    background-color: rgba(125, 177, 255, 0.18);
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
    background-color: rgba(134, 199, 157, 0.12);
}}

QPushButton#stopButton {{
    border-color: {c['error']};
    color: {c['error']};
}}

QPushButton#stopButton:hover {{
    background-color: rgba(217, 135, 135, 0.12);
}}

QPushButton#pauseButton {{
    border-color: {c['accent_marker']};
    color: {c['accent_marker']};
}}

QPushButton#pauseButton:hover {{
    background-color: rgba(224, 186, 124, 0.12);
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
    color: {c['text_secondary']};
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
    border: 1px solid {c['border_strong']};
    color: {c['text_primary']};
    padding: 4px 8px;
    border-radius: 4px;
}}
"""


STYLESHEET = _build_stylesheet(COLORS)

SYNTAX_COLORS = {
    'keyword': '#9dbdff',
    'string': '#9cc9a8',
    'comment': '#8f8b82',
    'number': '#dcb786',
    'function': '#b8c7e6',
    'class': '#a9b7d2',
    'decorator': '#baa57f',
}

PLOT_COLORS = {
    'bg': '#121210',
    'grid_major': '#343430',
    'grid_minor': '#292927',
    'grid_alpha': 0.12,
    'grid_origin_alpha': 0.18,
    'axis': '#cbc9c4',
    'marker': '#e0ba7c',
    'selection': '#7db1ff',
    'success': '#86c79d',
    'error': '#d98787',
}

ROW_COLORS = [
    '#7db1ff', '#a48bff', '#86c79d', '#e0ba7c', '#caa2d9',
    '#89c4c1', '#d5bf95', '#9faece', '#bfcead', '#d0a9a0',
]

ANTHROPIC_THEME = Theme(
    name='Anthropic Dark',
    id='anthropic',
    colors=COLORS,
    stylesheet=STYLESHEET,
    syntax_colors=SYNTAX_COLORS,
    plot_colors=PLOT_COLORS,
    row_colors=ROW_COLORS,
)
