"""Instrument panel dark theme for PyProbe."""

from .base import Theme


COLORS = {
    'bg_darkest': '#0f1217',
    'bg_dark': '#141a21',
    'bg_medium': '#1a222c',
    'bg_light': '#232e3a',

    'border_dark': '#2a3440',
    'border_medium': '#344252',
    'border_light': '#425265',

    'neon_cyan': '#4fc3f7',
    'neon_magenta': '#7fb8ff',
    'neon_green': '#6bd47a',
    'neon_yellow': '#ffbf5f',
    'neon_red': '#ff6b6b',
    'neon_orange': '#ffad42',

    'text_primary': '#eaf1f8',
    'text_secondary': '#b6c3d1',
    'text_muted': '#7f92a4',

    'accent_primary': '#4fc3f7',
    'accent_secondary': '#7fb8ff',
    'accent_marker': '#ffbf5f',
    'success': '#6bd47a',
    'warning': '#ffad42',
    'error': '#ff6b6b',
    'border_default': '#344252',
    'border_strong': '#425265',
}


def _build_stylesheet(c: dict) -> str:
    return f"""
QMainWindow {{
    background-color: {c['bg_darkest']};
}}

QWidget {{
    background-color: {c['bg_dark']};
    color: {c['text_primary']};
    font-family: \"Inter\", \"IBM Plex Sans\", \"SF Pro Text\", \"Segoe UI\", \"Noto Sans\", sans-serif;
    font-size: 12px;
}}

QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    font-family: \"JetBrains Mono\", \"IBM Plex Mono\", \"SF Mono\", \"Consolas\", \"Menlo\", monospace;
}}

QToolBar {{
    background-color: {c['bg_darkest']};
    border-bottom: 1px solid {c['border_strong']};
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
    background-color: rgba(79, 195, 247, 0.10);
    border-color: {c['accent_primary']};
}}

QPushButton:pressed {{
    background-color: rgba(79, 195, 247, 0.18);
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
    background-color: rgba(107, 212, 122, 0.12);
}}

QPushButton#stopButton {{
    border-color: {c['error']};
    color: {c['error']};
}}

QPushButton#stopButton:hover {{
    background-color: rgba(255, 107, 107, 0.12);
}}

QPushButton#pauseButton {{
    border-color: {c['accent_marker']};
    color: {c['accent_marker']};
}}

QPushButton#pauseButton:hover {{
    background-color: rgba(255, 191, 95, 0.12);
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
    'keyword': '#7fb8ff',
    'string': '#87d9a0',
    'comment': '#7f92a4',
    'number': '#ffbf5f',
    'function': '#4fc3f7',
    'class': '#9ec8f0',
    'decorator': '#ffad42',
}

PLOT_COLORS = {
    'bg': '#0f1217',
    'grid_major': '#344252',
    'grid_minor': '#2a3440',
    'grid_alpha': 0.14,
    'grid_origin_alpha': 0.22,
    'axis': '#b6c3d1',
    'marker': '#ffbf5f',
    'selection': '#4fc3f7',
    'success': '#6bd47a',
    'error': '#ff6b6b',
}

ROW_COLORS = [
    '#4fc3f7', '#6bd47a', '#ffbf5f', '#7fb8ff', '#ffad42',
    '#65d7ff', '#8be399', '#ffd089', '#9dc8ff', '#ffc371',
]

INSTRUMENT_PANEL_THEME = Theme(
    name='Instrument Panel Dark',
    id='instrument-panel',
    colors=COLORS,
    stylesheet=STYLESHEET,
    syntax_colors=SYNTAX_COLORS,
    plot_colors=PLOT_COLORS,
    row_colors=ROW_COLORS,
)
