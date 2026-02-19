"""Base theme protocol types."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """Serializable theme descriptor used by ThemeManager and widgets."""

    name: str
    id: str
    colors: dict[str, str]
    stylesheet: str
    syntax_colors: dict[str, str]
    plot_colors: dict[str, str]
    row_colors: list[str]
