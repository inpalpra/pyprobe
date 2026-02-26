from pathlib import Path


class PathSanitizer:
    """Replaces user home-directory paths with <USER_HOME> in any string."""

    PLACEHOLDER = "<USER_HOME>"

    @classmethod
    def sanitize(cls, text: str) -> str:
        """Return text with all occurrences of the user home dir replaced."""
        home = str(Path.home())
        return text.replace(home, cls.PLACEHOLDER)
