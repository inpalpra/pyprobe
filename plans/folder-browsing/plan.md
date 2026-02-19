# Folder Browsing — Open Folder, Select File, Probe

## Problem

PyProbe currently operates on a single file: user opens one `.py` file via CLI arg or the Open button, and that file gets loaded into the CodeViewer. There is no way to browse a project folder, navigate between files, or switch scripts without re-opening via the file dialog.

## Goal

Allow users to open an entire folder. A file tree appears showing the directory contents. User clicks a file in the tree → it loads into CodeViewer. User can then run it, probe variables, etc. — same workflow as today, but with folder navigation built in.

## Design Principles (from Constitution)

- **C1 (Gesture, Not Configuration):** Opening a folder should be one action. Selecting a file is one click.  
- **C11 (Discovery Beats Documentation):** File tree is visible, browseable. No hidden menus.  
- **C12 (Tool Must Disappear):** File tree shouldn't dominate — it's navigation, not the focus. Collapsible.

---

## Architecture

### Current Layout

```
┌──────────────────────────────────────────────┐
│  ControlBar: [Open] [Run] [Stop] [Loop] [Watch] │
├──────────────┬───────────────┬───────────────┤
│  CodeGutter  │  ProbePanels  │ WatchSidebar  │
│  + CodeViewer│  (center)     │ (hidden)      │
├──────────────┴───────────────┴───────────────┤
│  DockBar (hidden when empty)                 │
└──────────────────────────────────────────────┘
```

### Proposed Layout

```
┌──────────────────────────────────────────────────────┐
│  ControlBar: [Open▾] [Run] [Stop] [Loop] [Watch]    │
├────────┬──────────────┬───────────────┬──────────────┤
│ File   │  CodeGutter  │  ProbePanels  │ WatchSidebar │
│ Tree   │  + CodeViewer│  (center)     │ (hidden)     │
│ (left) │              │               │              │
├────────┴──────────────┴───────────────┴──────────────┤
│  DockBar (hidden when empty)                         │
└──────────────────────────────────────────────────────┘
```

The file tree inserts **left of the code container** in the main horizontal splitter.

---

## Components

### 1. FileTreePanel (`pyprobe/gui/file_tree.py`) — NEW

A `QWidget` containing a `QTreeView` + `QFileSystemModel`.

```
FileTreePanel
├── QTreeView (directory contents)
│   └── QFileSystemModel (filtered to *.py + folders)
├── Signals:
│   └── file_selected(str)    # emitted on single-click or Enter
└── Methods:
    ├── set_root(folder_path)  # set root directory
    ├── highlight_file(path)   # highlight the currently-loaded file
    └── clear()                # reset to no-folder state
```

**Behavior:**
- `QFileSystemModel` rooted at the opened folder
- Name filters: `["*.py"]` — show only Python files (+ folders that contain them)
- Single click on a `.py` file → emits `file_selected(path)`
- Currently-loaded file gets a highlight/bold treatment
- Tree header shows just the folder name
- Hidden by default (shown when a folder is opened)
- Reasonable default width: ~200px

**Style:**
- Dark theme consistent with cyberpunk aesthetic
- Matches existing widget colors

### 2. CLI Changes (`pyprobe/__main__.py`)

**Option A (recommended): Auto-detect file vs. folder**
- If `args.script` is a directory → treat as folder open
- If `args.script` is a file → current behavior (unchanged)
- No new flags needed

```python
# In __main__.py, before run_app:
script_path = args.script
folder_path = None

if script_path and os.path.isdir(script_path):
    folder_path = script_path
    script_path = None

sys.exit(run_app(
    script_path=script_path,
    folder_path=folder_path,
    ...
))
```

**`run_app()` signature** adds `folder_path: str = None`.

### 3. ControlBar Changes (`pyprobe/gui/control_bar.py`)

**Open button becomes a dropdown/split button:**
- Left-click: "Open File..." (current behavior)
- Or add a small menu: "Open File..." / "Open Folder..."
- New signal: `open_folder_clicked`

**Simpler alternative:** Single "Open" button. If nothing is loaded, shows a menu. If the user uses Ctrl+O → file, Ctrl+Shift+O → folder. This matches VS Code conventions.

**Recommended approach:** Add `open_folder_clicked` signal. Wire a `QMenu` to Open button with two actions.

### 4. MainWindow Changes (`pyprobe/gui/main_window.py`)

#### Layout (`_setup_ui`)

```python
# Add FileTreePanel to splitter BEFORE code container
self._file_tree = FileTreePanel()
self._file_tree.setVisible(False)  # hidden until folder opened
splitter.addWidget(self._file_tree)
splitter.addWidget(code_container)
splitter.addWidget(self._probe_container)
splitter.addWidget(self._scalar_watch_sidebar)
splitter.setSizes([0, 400, 800, 0])  # tree collapsed when hidden
```

#### Signals (`_setup_signals`)

```python
self._control_bar.open_folder_clicked.connect(self._on_open_folder)
self._file_tree.file_selected.connect(self._on_file_tree_selected)
```

#### New Methods

```python
def _on_open_folder(self):
    """Open folder dialog."""
    folder = QFileDialog.getExistingDirectory(self, "Open Folder", "")
    if folder:
        self._load_folder(folder)

def _load_folder(self, folder_path: str):
    """Load a folder into the file tree."""
    self._folder_path = os.path.abspath(folder_path)
    self._file_tree.set_root(folder_path)
    self._file_tree.setVisible(True)
    # Resize splitter to show tree
    self._main_splitter.setSizes([200, 400, 800, 0])
    self._status_bar.showMessage(f"Opened folder: {folder_path}")

def _on_file_tree_selected(self, file_path: str):
    """Handle file selection from file tree."""
    if file_path == self._script_path:
        return  # already loaded
    # Clear existing probes before loading new file
    self._clear_all_probes()
    self._load_script(file_path)
    self._file_tree.highlight_file(file_path)
```

#### Probe Cleanup on File Switch

When switching files within a folder, existing probes must be cleaned up:
- Save current probes to `.pyprobe` sidecar (already happens via `_save_probe_settings`)
- Remove all active probes (panels, overlays, gutter markers)
- Load new file's probes from its sidecar

Need a `_clear_all_probes()` method that:
1. Calls `_save_probe_settings()` for current file
2. Removes all probe panels via `ProbeController`
3. Clears gutter markers
4. Resets `_active_probes` in CodeViewer

### 5. `run_app()` Changes (`pyprobe/gui/app.py`)

```python
def run_app(script_path=None, folder_path=None, probes=None, ...):
    window = MainWindow(script_path=script_path, probes=probes, ...)
    if folder_path:
        window._load_folder(folder_path)
```

---

## What Does NOT Change

- **CodeViewer** — still shows one file at a time. No tabs.
- **Runner/Tracer** — runs whatever `_script_path` is set to. Anchor-based filtering already supports any file.
- **FileWatcher** — already replaces watch when `watch_file()` is called with a new path.
- **Probe persistence** — `.pyprobe` sidecars already per-file. Switching files naturally loads/saves the right sidecar.
- **IPC/Messages** — unchanged. Anchors carry file paths.

---

## Implementation Milestones

### M1: FileTreePanel widget (standalone)
- [ ] Create `pyprobe/gui/file_tree.py` with `FileTreePanel`
- [ ] `QTreeView` + `QFileSystemModel`, `.py` filter
- [ ] `file_selected` signal on click
- [ ] Highlight support for current file
- [ ] Dark theme styling

### M2: Wire into MainWindow
- [ ] Add `FileTreePanel` to splitter layout
- [ ] `_on_open_folder()` + `_load_folder()` 
- [ ] `_on_file_tree_selected()` → `_load_script()`
- [ ] `_clear_all_probes()` method for clean file switching
- [ ] Splitter sizing logic (show/hide tree)

### M3: ControlBar + CLI
- [ ] Open button dropdown: "Open File..." / "Open Folder..."
- [ ] `open_folder_clicked` signal
- [ ] CLI auto-detect file vs. folder
- [ ] `run_app()` accepts `folder_path`

### M4: Polish
- [ ] Keyboard shortcut: Ctrl+Shift+O for Open Folder
- [ ] Status bar shows folder name when folder is open
- [ ] Double-click file in tree → load + auto-run
- [ ] Tree collapses/expands gracefully
- [ ] Handle edge cases: empty folders, no .py files, nested folders

### M5: Multi-file probe set (Option C)
- [ ] When switching files, keep OTHER files' probes active in the tracer
- [ ] Send probes for all browsed files to runner, not just the viewed file
- [ ] Panels for non-viewed-file probes still show data when script runs
- [ ] Gutter/CodeViewer only show current file's probes (natural)
- [ ] `_clear_all_probes` scoped to current file only (prep done in M2)

---

## Resolved Questions

1. **File tree shows `.py` files + folders only.** Data files aren't runnable.

2. **Single-file view.** No tabs. Tree is the navigator.

3. **Probes persist per-file** via `.pyprobe` sidecars (already works).

4. **Sibling imports:** Start with **Option A (run-file-only)**.
   - Run button runs the file shown in CodeViewer
   - User can browse to imported files, read code, set probes
   - Probes fire when the entry-point script is run (trace is anchor-driven, not file-driven)
   - `_clear_all_probes` only clears probes for the **current** file, not all files
   - **M5** adds Option C: multi-file probe set (probes from all browsed files stay active simultaneously)
