"""Global theme manager for runtime theme switching."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from .base import Theme


class ThemeManager(QObject):
    """Singleton manager that owns active theme and application stylesheet."""

    theme_changed = pyqtSignal(object)
    _instance: Optional["ThemeManager"] = None

    def __init__(self, app: Optional[QApplication] = None):
        super().__init__()
        self._app = app or QApplication.instance()
        self._current: Optional[Theme] = None

    @classmethod
    def instance(cls, app: Optional[QApplication] = None) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls(app)
        elif app is not None:
            cls._instance._app = app
        return cls._instance

    def set_theme(self, theme_id: str) -> None:
        from . import THEMES

        theme = THEMES.get(theme_id)
        if theme is None:
            raise ValueError(f"Unknown theme id: {theme_id}")

        if self._app is None:
            self._app = QApplication.instance()

        if self._app is not None:
            # Global mandate: Monospaced font everywhere
            mono_font = QFont("JetBrains Mono")
            mono_font.setStyleHint(QFont.StyleHint.Monospace)
            self._app.setFont(mono_font)

            if theme_id == "cyberpunk":
                from .cyberpunk import _apply_font_and_palette

                _apply_font_and_palette(self._app)
            else:
                self._app.setPalette(self._app.style().standardPalette())
            self._app.setStyleSheet(theme.stylesheet)

        self._current = theme
        self.theme_changed.emit(theme)

    @property
    def current(self) -> Theme:
        if self._current is None:
            from . import DEFAULT_THEME_ID

            self.set_theme(DEFAULT_THEME_ID)
        return self._current

    def available(self) -> list[Theme]:
        from . import THEMES

        return list(THEMES.values())
