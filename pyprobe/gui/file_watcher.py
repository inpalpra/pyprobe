"""File system watcher for auto-reload on save."""
from PyQt6.QtCore import QObject, pyqtSignal, QFileSystemWatcher
from typing import Set, Optional


class FileWatcher(QObject):
    """Watch files for modifications and emit reload signals."""

    file_changed = pyqtSignal(str)  # Emits filepath

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._watcher = QFileSystemWatcher(self)
        self._watched: Set[str] = set()
        self._watcher.fileChanged.connect(self._on_file_changed)

    def watch_file(self, filepath: str) -> None:
        """Start watching a file for changes."""
        if filepath not in self._watched:
            self._watcher.addPath(filepath)
            self._watched.add(filepath)

    def unwatch_file(self, filepath: str) -> None:
        """Stop watching a file."""
        if filepath in self._watched:
            self._watcher.removePath(filepath)
            self._watched.discard(filepath)

    def unwatch_all(self) -> None:
        """Stop watching all files."""
        for fp in list(self._watched):
            self.unwatch_file(fp)

    def _on_file_changed(self, filepath: str) -> None:
        """Handle file change notification."""
        # QFileSystemWatcher may remove the path after change (depending on OS)
        # Re-add it to keep watching
        if filepath not in self._watcher.files():
            self._watcher.addPath(filepath)
        self.file_changed.emit(filepath)
