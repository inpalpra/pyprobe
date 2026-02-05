# Plan 3: File Watcher & Anchor Mapping

**Focus:** Watch files for changes, preserve anchors across reloads.

**Branch:** `m1/file-watcher`

**Dependencies:** Plan 0 (ProbeAnchor), Plan 1 (ASTLocator)

**Complexity:** Medium (M)

**UX Requirements Addressed:**
- Live Source Sync (M1 requirement)
- File watcher for auto-reload on save (requirement #5)
- Invalidated anchor visual state (requirement)

---

## Files to Create

### `pyprobe/gui/file_watcher.py`

```python
"""File system watcher for auto-reload on save."""
from PyQt6.QtCore import QObject, pyqtSignal, QFileSystemWatcher
from typing import Set, Optional

class FileWatcher(QObject):
    """Watch files for modifications and emit reload signals.

    Debounces rapid changes (editors often write multiple times on save).
    """

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
```

### `pyprobe/analysis/anchor_mapper.py`

Maps probe anchors from old source to new source after file edits.

**Mapping Strategy:**
1. **High confidence (1.0):** Same (line, col, symbol, func) exists
2. **Medium confidence (0.7):** Same (symbol, func) exists nearby
3. **Low confidence (0.4):** Only symbol exists anywhere
4. **Invalid (0.0):** Cannot find symbol

**Key classes:**
- `AnchorMapping`: Result dataclass with old_anchor, new_anchor, confidence
- `AnchorMapper`: Main class with `map_anchor()`, `get_invalidated()`, etc.

**Implementation:** Uses `difflib.SequenceMatcher` for line mapping.

See main plan file for full code (~140 lines).

---

## Key Implementation Notes

### Line Mapping with difflib

```python
def _compute_line_map(self) -> Dict[int, int]:
    old_lines = self._old_source.splitlines()
    new_lines = self._new_source.splitlines()

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    line_map = {}

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for offset in range(i2 - i1):
                line_map[i1 + offset + 1] = j1 + offset + 1  # 1-indexed

    return line_map
```

### Anchor Preservation Flow

```
File changed signal
    ↓
Read old source from code viewer
Read new source from disk
    ↓
AnchorMapper(old_source, new_source, filepath)
    ↓
For each active anchor:
    mapping = mapper.map_anchor(anchor)
    if mapping.new_anchor is None:
        mark_invalid(anchor)
    else:
        update_anchor_position(mapping.new_anchor)
    ↓
Reload code viewer
Re-apply valid probe highlights
```

---

## Verification

```bash
python -c "
from pyprobe.analysis.anchor_mapper import AnchorMapper
from pyprobe.core.anchor import ProbeAnchor

old = '''
def foo():
    x = 1
    return x
'''

new = '''
def foo():
    # Added comment
    x = 1
    return x
'''

mapper = AnchorMapper(old, new, '/test.py')
anchor = ProbeAnchor('/test.py', 3, 4, 'x', 'foo')
result = mapper.map_anchor(anchor)
print(f'Old line {anchor.line} -> New line {result.new_anchor.line}')
# Should print: Old line 3 -> New line 4
"
```

---

## Merge Conflict Risk

**None** - All new files.
