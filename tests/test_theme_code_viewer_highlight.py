"""Tests for CodeViewer highlighting and theme interactions."""

import pytest
from PyQt6.QtGui import QFontMetricsF
from pyprobe.gui.code_viewer import CodeViewer
from pyprobe.gui.theme.ocean import OCEAN_THEME

def test_code_viewer_maintains_monospace_in_ocean_theme(qapp):
    """
    Ensure the code viewer maintains a monospace font when the Ocean theme is applied.
    Ocean theme uses a global variable-width font (Inter, etc.) on QWidget, which
    can cascade into QPlainTextEdit and override the python setFont() call if not
    properly protected by the stylesheet.
    """
    # Apply the ocean theme globally, similar to how PyProbe does it
    from pyprobe.gui.theme.theme_manager import ThemeManager
    ThemeManager.instance().set_theme('ocean')

    viewer = CodeViewer()
    # Trigger theme application on the widget
    viewer._apply_theme(OCEAN_THEME)

    # Check font metrics of the actual viewer
    fm = QFontMetricsF(viewer.font())
    
    # In a monospace font, 'i' and 'm' and 'w' should have the exact same advance width
    width_i = fm.horizontalAdvance('i')
    width_m = fm.horizontalAdvance('m')
    width_w = fm.horizontalAdvance('w')

    assert width_i == width_m, f"Not a monospace font! 'i' width: {width_i}, 'm' width: {width_m}"
    assert width_m == width_w, f"Not a monospace font! 'm' width: {width_m}, 'w' width: {width_w}"
