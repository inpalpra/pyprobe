"""Apple-inspired 'Daylight' light theme for PyProbe."""

from .base import Theme


COLORS = {
    # Backgrounds — bg_darkest is the lightest (main canvas); bg_light the deepest
    'bg_darkest': '#FFFFFF',   # pure white — main canvas, code viewer
    'bg_dark':    '#F5F5F7',   # Apple signature off-white — panel backgrounds
    'bg_medium':  '#EBEBED',   # secondary areas, hover states
    'bg_light':   '#E1E1E3',   # pressed / active states

    # Borders
    'border_dark':    '#D2D2D7',   # very subtle separator
    'border_medium':  '#C7C7CC',   # standard macOS separator
    'border_light':   '#BEBEC5',   # medium-weight border
    'border_default': '#D2D2D7',
    'border_strong':  '#AEAEB2',

    # Text
    'text_primary':   '#1D1D1F',   # Apple near-black
    'text_secondary': '#6E6E73',   # Apple secondary gray
    'text_muted':     '#AEAEB2',   # Apple tertiary / disabled

    # Accents — refined Apple system palette, replacing neon keys
    'neon_cyan':    '#0071E3',   # Apple blue (primary CTA)
    'neon_magenta': '#7F5FFF',   # soft purple
    'neon_green':   '#34C759',   # Apple system green
    'neon_yellow':  '#F59E0B',   # warm amber
    'neon_red':     '#FF3B30',   # Apple system red
    'neon_orange':  '#FF9500',   # Apple system orange

    # Semantic aliases
    'accent_primary':   '#0071E3',
    'accent_secondary': '#7F5FFF',
    'accent_marker':    '#F59E0B',
    'success': '#34C759',
    'warning': '#FF9500',
    'error':   '#FF3B30',
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

QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    font-family: \"SF Mono\", \"JetBrains Mono\", \"Menlo\", \"Consolas\", \"Monaco\";
}}

QToolBar {{
    background-color: {c['bg_darkest']};
    border-bottom: 1px solid {c['border_default']};
    padding: 4px;
    spacing: 8px;
}}

QToolBar QToolButton {{
    background-color: transparent;
    border: 1px solid {c['border_medium']};
    border-radius: 4px;
    padding: 6px 12px;
    color: {c['text_primary']};
    font-weight: 600;
}}

QToolBar QToolButton:hover {{
    background-color: {c['bg_medium']};
    border-color: {c['accent_primary']};
    color: {c['accent_primary']};
}}

QToolBar QToolButton:pressed {{
    background-color: {c['bg_light']};
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
    background-color: {c['bg_dark']};
    border: 1px solid {c['border_dark']};
    border-radius: 3px;
    padding: 8px;
    margin: 2px 0px;
}}

QListWidget::item:selected {{
    background-color: rgba(0, 113, 227, 0.12);
    border-color: {c['accent_primary']};
}}

QListWidget::item:hover {{
    border-color: {c['border_strong']};
}}

QLineEdit {{
    background-color: {c['bg_darkest']};
    border: 1px solid {c['border_medium']};
    border-radius: 4px;
    padding: 6px;
    color: {c['text_primary']};
    selection-background-color: {c['accent_primary']};
    selection-color: #FFFFFF;
}}

QLineEdit:focus {{
    border-color: {c['accent_primary']};
}}

QLineEdit::placeholder {{
    color: {c['text_muted']};
}}

QPushButton {{
    background-color: {c['bg_dark']};
    border: 1px solid {c['border_medium']};
    border-radius: 4px;
    padding: 8px 16px;
    color: {c['text_primary']};
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {c['bg_medium']};
    border-color: {c['accent_primary']};
}}

QPushButton:pressed {{
    background-color: {c['bg_light']};
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
    background-color: rgba(52, 199, 89, 0.12);
}}

QPushButton#stopButton {{
    border-color: {c['error']};
    color: {c['error']};
}}

QPushButton#stopButton:hover {{
    background-color: rgba(255, 59, 48, 0.12);
}}

QPushButton#pauseButton {{
    border-color: {c['accent_marker']};
    color: {c['accent_marker']};
}}

QPushButton#pauseButton:hover {{
    background-color: rgba(245, 158, 11, 0.12);
}}

QScrollBar:vertical {{
    background-color: {c['bg_dark']};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {c['border_strong']};
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
    background-color: {c['bg_dark']};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {c['border_strong']};
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
    background-color: {c['bg_darkest']};
    border: 1px solid {c['border_default']};
    color: {c['text_primary']};
    padding: 4px 8px;
    border-radius: 4px;
}}
"""


STYLESHEET = _build_stylesheet(COLORS)

SYNTAX_COLORS = {
    'keyword':   '#9B2393',   # Xcode purple
    'string':    '#C41A16',   # Xcode brick red
    'comment':   '#6C7986',   # Xcode muted teal-gray
    'number':    '#1C00CF',   # Xcode dark blue
    'function':  '#3900A0',   # Xcode deep indigo
    'class':     '#5C2699',   # Xcode purple-blue
    'decorator': '#9B2393',   # matches keyword
}

PLOT_COLORS = {
    'bg':                '#FFFFFF',   # white plot canvas
    'grid_major':        '#E0E0E4',   # barely-visible light gray
    'grid_minor':        '#F0F0F2',   # almost invisible minor grid
    'grid_alpha':         0.9,
    'grid_origin_alpha':  0.95,
    'axis':              '#6E6E73',   # secondary gray for axis labels
    'marker':            '#F59E0B',   # amber marker
    'selection':         '#0071E3',   # Apple blue selection
    'success':           '#34C759',
    'error':             '#FF3B30',
}

# Apple system colors — all verified for contrast on white
ROW_COLORS = [
    '#0071E3',   # Apple Blue
    '#34C759',   # Apple Green
    '#FF9500',   # Apple Orange
    '#AF52DE',   # Apple Purple
    '#FF3B30',   # Apple Red
    '#5AC8FA',   # Apple Sky Blue
    '#FF2D55',   # Apple Pink
    '#5856D6',   # Apple Indigo
    '#30B0C7',   # Cyan
    '#FF6B35',   # Deep Orange
]

LIGHT_THEME = Theme(
    name='Daylight',
    id='light',
    colors=COLORS,
    stylesheet=STYLESHEET,
    syntax_colors=SYNTAX_COLORS,
    plot_colors=PLOT_COLORS,
    row_colors=ROW_COLORS,
)
