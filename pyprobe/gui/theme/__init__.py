"""Theme and styling modules."""

from .base import Theme
from .anthropic import ANTHROPIC_THEME
from .cyberpunk import CYBERPUNK_THEME
from .instrument_panel import INSTRUMENT_PANEL_THEME
from .monokai import MONOKAI_THEME
from .ocean import OCEAN_THEME

THEMES: dict[str, Theme] = {
	CYBERPUNK_THEME.id: CYBERPUNK_THEME,
	MONOKAI_THEME.id: MONOKAI_THEME,
	OCEAN_THEME.id: OCEAN_THEME,
	INSTRUMENT_PANEL_THEME.id: INSTRUMENT_PANEL_THEME,
	ANTHROPIC_THEME.id: ANTHROPIC_THEME,
}

DEFAULT_THEME_ID = CYBERPUNK_THEME.id

__all__ = [
	"Theme",
	"THEMES",
	"DEFAULT_THEME_ID",
	"ANTHROPIC_THEME",
	"CYBERPUNK_THEME",
	"MONOKAI_THEME",
	"OCEAN_THEME",
	"INSTRUMENT_PANEL_THEME",
]
