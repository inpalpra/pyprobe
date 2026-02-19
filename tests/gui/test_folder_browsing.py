"""
Suite B — In-process pytest-qt tests for folder-browsing GUI state.

Each test creates MainWindow in-process, manipulates widgets, and asserts
internal state.  No real script subprocesses are started.

Fixture folder: regression/folder_test/
"""

import os
import time
from typing import List
from unittest.mock import patch, Mock

import pytest
from PyQt6.QtCore import QModelIndex
from PyQt6.QtGui import QColor

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.probe_persistence import get_sidecar_path
from pyprobe.gui.control_bar import ControlBar
from pyprobe.gui.file_tree import FileTreePanel
from pyprobe.gui.main_window import MainWindow

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(__file__)
REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
FOLDER_TEST_DIR = os.path.join(REPO_ROOT, "regression", "folder_test")
LOOP_SCRIPT = os.path.abspath(os.path.join(FOLDER_TEST_DIR, "loop_script.py"))
MAIN_ENTRY = os.path.abspath(os.path.join(FOLDER_TEST_DIR, "main_entry.py"))
REGRESSION_LOOP = os.path.abspath(os.path.join(REPO_ROOT, "regression", "loop.py"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pev(qapp, n: int = 5) -> None:
    """Flush the Qt event queue n times."""
    for _ in range(n):
        qapp.processEvents()


def _y_anchor(script_path: str = LOOP_SCRIPT) -> ProbeAnchor:
    """
    Build a ProbeAnchor for 'y' at line 2 of loop_script.py.

    loop_script.py line 2:  ``    for y in [10, 20, 30]:``
    Column 8 (0-indexed) is where 'y' sits.
    """
    return ProbeAnchor(
        file=os.path.abspath(script_path),
        line=2,
        col=8,
        symbol="y",
        func="main",
        is_assignment=True,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def win(qapp):
    """Plain MainWindow — no script loaded."""
    window = MainWindow()
    window.resize(1200, 800)
    window.show()
    qapp.processEvents()
    yield window
    window.close()
    qapp.processEvents()


@pytest.fixture
def cleanup_sidecar():
    """Remove loop_script.py sidecar before and after each test."""
    sidecar = get_sidecar_path(LOOP_SCRIPT)
    if sidecar.exists():
        sidecar.unlink()
    yield
    if sidecar.exists():
        sidecar.unlink()


# ===========================================================================
# B1 — File tree hidden on startup
# ===========================================================================

def test_file_tree_hidden_on_startup(win, qapp):
    """
    B1: File tree panel is invisible and occupies zero splitter width when no
    folder has been loaded.
    """
    assert not win._file_tree.isVisible(), "Tree must be hidden at startup"
    assert win._main_splitter.sizes()[0] == 0, "File-tree splitter slot must have zero width"


def test_file_tree_hidden_when_opening_single_file(win, qapp):
    """
    B1 variant: Loading a single script (not a folder) must keep the file tree
    hidden.
    """
    win._load_script(REGRESSION_LOOP)
    _pev(qapp)

    assert not win._file_tree.isVisible(), "Tree must stay hidden for single-file mode"


# ===========================================================================
# B2 — File tree shown after folder load
# ===========================================================================

def test_file_tree_shown_on_folder_load(win, qapp):
    """
    B2: Loading a folder reveals the file tree, sets a non-zero splitter
    width, updates the header label, and stores _folder_path.
    """
    assert not win._file_tree.isVisible(), "Precondition: tree hidden before folder load"

    win._load_folder(FOLDER_TEST_DIR)
    _pev(qapp)

    assert win._file_tree.isVisible(), "File tree must be visible after _load_folder"
    assert win._main_splitter.sizes()[0] > 0, "File-tree splitter slot must have non-zero width"
    assert win._folder_path == os.path.abspath(FOLDER_TEST_DIR)

    expected_header = os.path.basename(FOLDER_TEST_DIR).upper()
    assert win._file_tree._header.text() == expected_header, (
        f"Header should be '{expected_header}', got '{win._file_tree._header.text()}'"
    )


# ===========================================================================
# B3 — File tree shows only .py files
# ===========================================================================

def test_file_tree_shows_only_py_files(win, qapp, qtbot):
    """
    B3: The PyFileFilterProxy must pass .py files and subdirectories while
    hiding all other file types (e.g. .txt).
    """
    with qtbot.waitSignal(
        win._file_tree._fs_model.directoryLoaded, timeout=5000
    ):
        win._load_folder(FOLDER_TEST_DIR)

    _pev(qapp)

    fs_model = win._file_tree._fs_model
    proxy = win._file_tree._proxy

    # .txt file must be filtered out
    txt_path = os.path.join(FOLDER_TEST_DIR, "data_file.txt")
    txt_src = fs_model.index(txt_path)
    assert txt_src.isValid(), "QFileSystemModel must know about data_file.txt"
    assert not proxy.mapFromSource(txt_src).isValid(), (
        "data_file.txt must be filtered out by the proxy"
    )

    # .py file must pass the filter
    py_src = fs_model.index(LOOP_SCRIPT)
    assert proxy.mapFromSource(py_src).isValid(), (
        "loop_script.py must be visible in the proxy"
    )

    # Subdirectory containing .py files must be visible
    subdir_path = os.path.join(FOLDER_TEST_DIR, "subdir")
    subdir_src = fs_model.index(subdir_path)
    assert subdir_src.isValid(), "QFileSystemModel must know about subdir/"
    assert proxy.mapFromSource(subdir_src).isValid(), (
        "subdir/ must be visible (it contains nested .py files)"
    )


# ===========================================================================
# B4 — Clicking a file loads the script
# ===========================================================================

def test_file_tree_click_loads_script(win, qapp):
    """
    B4: Calling _on_file_tree_selected with a .py path sets _script_path,
    loads source into the code viewer, enables the control bar, and updates
    the status bar.
    """
    win._load_folder(FOLDER_TEST_DIR)
    _pev(qapp)

    win._on_file_tree_selected(LOOP_SCRIPT)
    _pev(qapp)

    assert win._script_path == LOOP_SCRIPT
    assert "for y in" in win._code_viewer.toPlainText(), (
        "Code viewer must contain loop_script.py source"
    )
    assert win._control_bar._script_loaded, "Control bar must report script as loaded"
    assert "loop_script.py" in win._status_bar.currentMessage(), (
        "Status bar must mention the loaded filename"
    )


# ===========================================================================
# B5 — Switching files clears old probes
# ===========================================================================

def test_file_switch_clears_old_probes(win, qapp):
    """
    B5: Selecting a different file clears all probe panels, empties the probe
    registry, and loads the new file's source into the code viewer.
    """
    win._load_folder(FOLDER_TEST_DIR)
    win._on_file_tree_selected(LOOP_SCRIPT)
    _pev(qapp)

    anchor = _y_anchor()
    win._on_probe_requested(anchor)
    _pev(qapp)

    assert anchor in win._probe_panels, "Precondition: probe must exist after adding"

    # Switch to a different file
    win._on_file_tree_selected(MAIN_ENTRY)
    _pev(qapp)

    assert win._probe_panels == {}, "All probe panels must be cleared on file switch"
    assert win._probe_registry.all_anchors == set(), "Registry must be empty after switch"
    assert "compute" in win._code_viewer.toPlainText(), (
        "Code viewer must contain main_entry.py source after switch"
    )


# ===========================================================================
# B6 — File switch saves sidecar; switch-back restores probes
# ===========================================================================

def test_file_switch_saves_sidecar(win, qapp, cleanup_sidecar):
    """
    B6a: Switching away from a file with active probes creates a .pyprobe
    sidecar file.
    """
    win._load_folder(FOLDER_TEST_DIR)
    win._on_file_tree_selected(LOOP_SCRIPT)
    _pev(qapp)

    win._on_probe_requested(_y_anchor())
    _pev(qapp)

    # Switch away — triggers _clear_all_probes() → _save_probe_settings()
    win._on_file_tree_selected(MAIN_ENTRY)
    _pev(qapp)

    sidecar = get_sidecar_path(LOOP_SCRIPT)
    assert sidecar.exists(), (
        "Switching away from a file with probes must create a .pyprobe sidecar"
    )


def test_file_switch_restores_probes_from_sidecar(win, qapp, cleanup_sidecar):
    """
    B6b: Switching back to a file whose sidecar has saved probes restores
    those probes via _process_cli_probes.
    """
    win._load_folder(FOLDER_TEST_DIR)
    win._on_file_tree_selected(LOOP_SCRIPT)
    _pev(qapp)

    win._on_probe_requested(_y_anchor())
    _pev(qapp)

    # Switch away to save the sidecar
    win._on_file_tree_selected(MAIN_ENTRY)
    _pev(qapp)

    assert get_sidecar_path(LOOP_SCRIPT).exists(), "Precondition: sidecar must be created"

    # Switch back — probe must be restored
    win._on_file_tree_selected(LOOP_SCRIPT)
    _pev(qapp)

    assert len(win._probe_panels) > 0, (
        "At least one probe must be restored from sidecar on switch-back"
    )


# ===========================================================================
# B7 — File switch during execution does not crash
# ===========================================================================

def test_file_switch_during_execution_not_crash(win, qapp):
    """
    B7: Switching files while the runner has been started must not raise any
    exception.  We simulate a 'running' state by loading a file and adding a
    probe (the IPC channel is None so no real subprocess is involved).
    """
    win._load_folder(FOLDER_TEST_DIR)
    win._on_file_tree_selected(LOOP_SCRIPT)
    _pev(qapp)

    win._on_probe_requested(_y_anchor())
    _pev(qapp)

    # Simulate in-flight state: monkey-patch the is_running property
    class _FakeRunner:
        """Thin wrapper that impersonates ScriptRunner with is_running=True."""
        is_running = True
        ipc = None
        user_stopped = False

        def __init__(self, real):
            self._real = real

        def __getattr__(self, name):
            return getattr(self._real, name)

    real_runner = win._script_runner
    win._script_runner = _FakeRunner(real_runner)

    try:
        win._on_file_tree_selected(MAIN_ENTRY)
        _pev(qapp)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"File switch during execution raised an unexpected exception: {exc!r}")
    finally:
        win._script_runner = real_runner  # restore

    # Main window is still responsive
    assert win._script_path == MAIN_ENTRY


# ===========================================================================
# B8 — Re-selecting the same file is a no-op
# ===========================================================================

def test_reselect_same_file_no_op(win, qapp):
    """
    B8: Calling _on_file_tree_selected with the already-loaded path must
    return early without clearing probes or reloading the script.
    """
    win._load_folder(FOLDER_TEST_DIR)
    win._on_file_tree_selected(LOOP_SCRIPT)
    _pev(qapp)

    anchor = _y_anchor()
    win._on_probe_requested(anchor)
    _pev(qapp)

    assert anchor in win._probe_panels, "Precondition: probe must exist"
    panel_count_before = len(win._probe_panels)

    # Re-select same file — must be a no-op
    win._on_file_tree_selected(LOOP_SCRIPT)
    _pev(qapp)

    assert anchor in win._probe_panels, (
        "Re-selecting the same file must not clear probes"
    )
    assert len(win._probe_panels) == panel_count_before
    assert win._script_path == LOOP_SCRIPT


# ===========================================================================
# B9 — File tree highlight tracks selection
# ===========================================================================

def test_file_tree_highlight_tracks_selection(win, qapp):
    """
    B9: _file_tree._current_file always mirrors the most recently selected
    file, updating correctly on A → B → A sequences.
    """
    win._load_folder(FOLDER_TEST_DIR)
    _pev(qapp)

    win._on_file_tree_selected(LOOP_SCRIPT)
    _pev(qapp)
    assert win._file_tree._current_file == LOOP_SCRIPT, (
        "After selecting loop_script, _current_file must match"
    )

    win._on_file_tree_selected(MAIN_ENTRY)
    _pev(qapp)
    assert win._file_tree._current_file == MAIN_ENTRY, (
        "After selecting main_entry, _current_file must match"
    )

    win._on_file_tree_selected(LOOP_SCRIPT)
    _pev(qapp)
    assert win._file_tree._current_file == LOOP_SCRIPT, (
        "After re-selecting loop_script, _current_file must match"
    )


# ===========================================================================
# B10 — Open-file dialog starts in the loaded folder
# ===========================================================================

def test_open_file_dialog_starts_in_folder(win, qapp):
    """
    B10: When a folder is loaded, 'Open File...' must open the QFileDialog
    with start_dir == _folder_path.
    """
    win._load_folder(FOLDER_TEST_DIR)
    _pev(qapp)

    with patch(
        "pyprobe.gui.main_window.QFileDialog.getOpenFileName",
        return_value=("", ""),
    ) as mock_dialog:
        win._on_open_script()
        _pev(qapp)

    assert mock_dialog.called, "QFileDialog.getOpenFileName must have been called"
    # Positional signature: getOpenFileName(parent, caption, dir, filter)
    pos_args = mock_dialog.call_args[0]
    start_dir = pos_args[2]
    assert start_dir == os.path.abspath(FOLDER_TEST_DIR), (
        f"File dialog must start in the loaded folder; got '{start_dir}'"
    )


# ===========================================================================
# B11 — _clear_all_probes cleans every container
# ===========================================================================

def test_clear_all_probes_cleans_everything(win, qapp):
    """
    B11: _clear_all_probes() must leave _probe_panels, _probe_metadata,
    _probe_registry, _scalar_watch_sidebar._scalars, and the CLI lists all
    empty.
    """
    win._load_script(LOOP_SCRIPT)
    _pev(qapp)

    # Add a graphical probe
    anchor = _y_anchor()
    win._on_probe_requested(anchor)
    _pev(qapp)

    # Add a scalar directly to the sidebar (simulates Alt+click)
    scalar_anchor = ProbeAnchor(
        file=LOOP_SCRIPT,
        line=2,
        col=8,
        symbol="y",
        func="main",
        is_assignment=True,
    )
    win._scalar_watch_sidebar.add_scalar(scalar_anchor, QColor("#00ffff"))
    _pev(qapp)

    # Set non-empty CLI lists to verify they get reset
    win._cli_probes = ["2:y:1"]
    win._cli_watches = ["2:y:1"]
    win._cli_overlays = ["y:2:z:1"]

    # Act
    win._clear_all_probes()
    _pev(qapp)

    assert win._probe_panels == {}, "_probe_panels must be empty after clear"
    assert win._probe_controller._probe_metadata == {}, "_probe_metadata must be empty after clear"
    assert win._probe_registry.all_anchors == set(), "Registry must be empty after clear"
    assert win._scalar_watch_sidebar._scalars == {}, "Scalar sidebar must be empty after clear"
    assert win._cli_probes == [], "_cli_probes must be reset"
    assert win._cli_watches == [], "_cli_watches must be reset"
    assert win._cli_overlays == [], "_cli_overlays must be reset"


# ===========================================================================
# Suite C — Stress / Edge Cases
# ===========================================================================

# ---------------------------------------------------------------------------
# C-level helpers
# ---------------------------------------------------------------------------

def _make_py_file(directory: str, name: str, content: str = "x = 1\n") -> str:
    """Write a .py file into *directory* and return its absolute path."""
    path = os.path.join(directory, name)
    with open(path, "w") as f:
        f.write(content)
    return os.path.abspath(path)


def _collect_leaf_files(proxy, fs_model, parent_index: QModelIndex) -> List[str]:
    """Recursively collect all visible file paths from a proxy model."""
    paths: List[str] = []
    for row in range(proxy.rowCount(parent_index)):
        idx = proxy.index(row, 0, parent_index)
        source_idx = proxy.mapToSource(idx)
        if not source_idx.isValid():
            continue
        file_info = fs_model.fileInfo(source_idx)
        if file_info.isFile():
            paths.append(file_info.absoluteFilePath())
        elif file_info.isDir():
            paths.extend(_collect_leaf_files(proxy, fs_model, idx))
    return paths


def _wait_for(condition, qapp, timeout: float = 2.0, interval: float = 0.05) -> bool:
    """Poll *condition()* until True or *timeout* seconds have elapsed."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        qapp.processEvents()
        if condition():
            return True
        time.sleep(interval)
    return False


# ---------------------------------------------------------------------------
# C-level fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def file_tree_panel(qapp):
    """Bare FileTreePanel, shown and torn down for each test."""
    panel = FileTreePanel()
    panel.resize(300, 500)
    panel.show()
    qapp.processEvents()
    yield panel
    panel.close()
    qapp.processEvents()


# ===========================================================================
# C1 — Rapid file switching (stress)
# ===========================================================================

class TestC1RapidFileSwitching:
    def test_rapid_file_switching(self, qapp, tmp_path):
        """
        C1: Switching between files 20 times in rapid succession must not crash.

        Asserts:
        - No unhandled exception during switching.
        - Final _script_path matches the last-selected file.
        - No probe panels were created (panel count stays 0).
        """
        # 5 distinct .py scripts — consecutive (i % 5) values always differ,
        # so the early-return guard in _on_file_tree_selected never fires.
        files = [
            _make_py_file(str(tmp_path), f"s{i}.py", f"x = {i}\n")
            for i in range(5)
        ]

        window = MainWindow()
        window._load_folder(str(tmp_path))
        qapp.processEvents()

        for i in range(20):
            window._on_file_tree_selected(files[i % len(files)])
            qapp.processEvents()

        expected = files[19 % len(files)]
        assert window._script_path == expected, (
            f"Expected _script_path={expected!r}, got {window._script_path!r}"
        )
        assert len(window._probe_panels) == 0, (
            f"Expected 0 probe panels after pure switching, "
            f"got {len(window._probe_panels)}"
        )

        window.close()
        qapp.processEvents()


# ===========================================================================
# C2 — Large folder (stress)
# ===========================================================================

class TestC2LargeFolder:
    def test_large_folder(self, qapp, tmp_path, file_tree_panel, qtbot):
        """
        C2: A folder with 100 .py files loads without freezing.

        Asserts:
        - At least one row is visible after QFileSystemModel finishes loading.
        - Clicking any visible .py row emits file_selected with a .py path.
        """
        for i in range(100):
            _make_py_file(str(tmp_path), f"module_{i:03d}.py", f"val = {i}\n")

        # Wait for the directory to be fully loaded (directoryLoaded fires when
        # QFileSystemModel has fetched all fileInfo for the target directory).
        with qtbot.waitSignal(
            file_tree_panel._fs_model.directoryLoaded,
            timeout=5000,
        ):
            file_tree_panel.set_root(str(tmp_path))

        proxy_root = file_tree_panel._tree.rootIndex()
        row_count = file_tree_panel._proxy.rowCount(proxy_root)
        assert row_count > 0, (
            "Tree should have at least one visible row for a 100-file folder"
        )

        # Find the first proxy row whose fileInfo confirms it is a .py file.
        received: List[str] = []
        file_tree_panel.file_selected.connect(received.append)

        clicked = False
        for row in range(row_count):
            idx = file_tree_panel._proxy.index(row, 0, proxy_root)
            src = file_tree_panel._proxy.mapToSource(idx)
            fi = file_tree_panel._fs_model.fileInfo(src)
            if fi.isFile() and fi.suffix() == "py":
                file_tree_panel._on_clicked(idx)
                qapp.processEvents()
                clicked = True
                break

        assert clicked, "Could not find a .py file row to click after directoryLoaded"
        assert len(received) == 1, "Expected file_selected to fire exactly once on click"
        assert received[0].endswith(".py"), (
            f"Expected a .py path, got {received[0]!r}"
        )


# ===========================================================================
# C3 — Empty folder
# ===========================================================================

class TestC3EmptyFolder:
    def test_empty_folder(self, qapp, tmp_path, file_tree_panel):
        """
        C3: An empty folder shows 0 rows in the tree without crashing.
        """
        file_tree_panel.set_root(str(tmp_path))
        for _ in range(5):
            qapp.processEvents()

        proxy_root = file_tree_panel._tree.rootIndex()
        row_count = file_tree_panel._proxy.rowCount(proxy_root)
        assert row_count == 0, (
            f"Expected 0 visible rows for an empty folder, got {row_count}"
        )


# ===========================================================================
# C4 — Folder with no .py files
# ===========================================================================

class TestC4NoPyFiles:
    def test_folder_with_no_py_files(self, qapp, tmp_path, file_tree_panel):
        """
        C4: A folder containing only .txt files exposes no selectable .py items.
        """
        for i in range(3):
            (tmp_path / f"notes_{i}.txt").write_text("hello\n")

        file_tree_panel.set_root(str(tmp_path))
        for _ in range(5):
            qapp.processEvents()

        proxy_root = file_tree_panel._tree.rootIndex()
        visible_files = _collect_leaf_files(
            file_tree_panel._proxy, file_tree_panel._fs_model, proxy_root
        )
        py_files = [p for p in visible_files if p.endswith(".py")]
        assert len(py_files) == 0, (
            f"Expected no .py items for a .txt-only folder, found: {py_files}"
        )


# ===========================================================================
# C5 — Deeply nested folder
# ===========================================================================

class TestC5DeeplyNested:
    def test_deeply_nested_folder(self, qapp, tmp_path, file_tree_panel):
        """
        C5: A script 5 directory levels deep can be navigated to via
        highlight_file() and is tracked in _current_file.
        """
        nested_dir = tmp_path / "a" / "b" / "c" / "d" / "e"
        nested_dir.mkdir(parents=True)
        script = nested_dir / "script.py"
        script.write_text("z = 99\n")

        file_tree_panel.set_root(str(tmp_path))
        for _ in range(5):
            qapp.processEvents()

        file_tree_panel.highlight_file(str(script))
        qapp.processEvents()

        assert file_tree_panel._current_file == str(script), (
            f"Expected _current_file={str(script)!r}, "
            f"got {file_tree_panel._current_file!r}"
        )


# ===========================================================================
# C6 — Folder with __pycache__
# ===========================================================================

class TestC6Pycache:
    def test_folder_with_pycache(self, qapp, tmp_path, file_tree_panel):
        """
        C6: .pyc byte-compiled files inside __pycache__ must not appear as
        selectable leaf items; only the real .py source file is visible.
        """
        (tmp_path / "main.py").write_text("x = 1\n")

        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "main.cpython-312.pyc").write_bytes(b"\x00\x00\x00\x00")

        file_tree_panel.set_root(str(tmp_path))
        for _ in range(5):
            qapp.processEvents()

        proxy_root = file_tree_panel._tree.rootIndex()
        visible_files = _collect_leaf_files(
            file_tree_panel._proxy, file_tree_panel._fs_model, proxy_root
        )

        pyc_files = [p for p in visible_files if p.endswith(".pyc")]
        assert len(pyc_files) == 0, (
            f".pyc files must not appear as selectable items: {pyc_files}"
        )

        py_files = [p for p in visible_files if p.endswith(".py")]
        assert any(p.endswith("main.py") for p in py_files), (
            f"Expected main.py to be visible, got: {py_files}"
        )


# ===========================================================================
# C7 — File modified externally while in tree
# ===========================================================================

class TestC7FileModified:
    def test_file_modified_externally_while_in_tree(self, qapp, tmp_path):
        """
        C7: When the loaded script is modified on disk, FileWatcher fires and
        _last_source_content is updated. The file tree remains selectable.

        NOTE: Relies on QFileSystemWatcher timing; polls up to 2 s.
        """
        script = _make_py_file(str(tmp_path), "watched.py", "x = 1\n")
        other = _make_py_file(str(tmp_path), "other.py", "y = 2\n")

        window = MainWindow()
        window._load_folder(str(tmp_path))
        window._on_file_tree_selected(script)
        qapp.processEvents()

        assert "x = 1" in (window._last_source_content or ""), (
            "Precondition: initial source content should contain 'x = 1'"
        )

        # Modify the file externally
        with open(script, "w") as f:
            f.write("x = 2  # modified\n")

        detected = _wait_for(
            lambda: "modified" in (window._last_source_content or ""),
            qapp,
        )
        assert detected, (
            "FileWatcher did not update _last_source_content after external "
            "file modification (waited 2 s)"
        )

        # File tree must remain usable after the modification event
        window._on_file_tree_selected(other)
        qapp.processEvents()
        assert window._script_path == other

        window.close()
        qapp.processEvents()


# ===========================================================================
# C8 — File deleted while selected
# ===========================================================================

class TestC8FileDeleted:
    def test_file_deleted_while_selected(self, qapp, tmp_path):
        """
        C8: Deleting the currently-loaded file while in the tree must not
        raise an unhandled exception.  The surviving file can still be opened.
        """
        script = _make_py_file(str(tmp_path), "ephemeral.py", "z = 0\n")
        survivor = _make_py_file(str(tmp_path), "survivor.py", "z = 1\n")

        window = MainWindow()
        window._load_folder(str(tmp_path))
        window._on_file_tree_selected(script)
        qapp.processEvents()

        # Delete the loaded file from disk
        os.remove(script)

        # Allow OS / Qt file-system events to propagate
        for _ in range(10):
            qapp.processEvents()
            time.sleep(0.05)

        # Must still be possible to select the surviving file without crash
        window._on_file_tree_selected(survivor)
        qapp.processEvents()
        assert window._script_path == survivor

        window.close()
        qapp.processEvents()


# ===========================================================================
# C9 — New file created in folder
# ===========================================================================

class TestC9NewFileCreated:
    def test_new_file_created_in_folder(self, qapp, tmp_path, file_tree_panel):
        """
        C9: A .py file written to disk after the folder is opened is
        auto-detected by QFileSystemModel and becomes queryable via index().

        NOTE: Relies on OS file-system notifications; polls up to 2 s.
        """
        file_tree_panel.set_root(str(tmp_path))
        for _ in range(5):
            qapp.processEvents()

        new_file = tmp_path / "new_module.py"
        new_file.write_text("a = 42\n")
        new_file_abs = str(new_file.resolve())

        # Wait for QFileSystemModel to recognise the new file
        # (index() returns a valid index only after the model has fetched it).
        appeared = _wait_for(
            lambda: file_tree_panel._fs_model.index(new_file_abs).isValid(),
            qapp,
        )
        assert appeared, (
            "QFileSystemModel should auto-detect the newly created .py file "
            "(waited 2 s)"
        )

        # The file must also pass the proxy filter so it is selectable.
        source_idx = file_tree_panel._fs_model.index(new_file_abs)
        proxy_idx = file_tree_panel._proxy.mapFromSource(source_idx)
        assert proxy_idx.isValid(), (
            "The new .py file must be visible through the PyFileFilterProxy"
        )


# ===========================================================================
# C10 — Open folder clears previous folder
# ===========================================================================

class TestC10FolderReplace:
    def test_open_folder_clears_previous_folder(self, qapp, tmp_path):
        """
        C10: Loading folder B after folder A replaces the tree state.

        Asserts:
        - _folder_path is updated to folder B's absolute path.
        - The file-tree header text reflects folder B's name.
        """
        folder_a = tmp_path / "folder_a"
        folder_b = tmp_path / "folder_b"
        folder_a.mkdir()
        folder_b.mkdir()
        _make_py_file(str(folder_a), "alpha.py")
        _make_py_file(str(folder_b), "beta.py")

        window = MainWindow()

        window._load_folder(str(folder_a))
        qapp.processEvents()
        assert window._folder_path == os.path.abspath(str(folder_a))

        window._load_folder(str(folder_b))
        qapp.processEvents()

        expected_path = os.path.abspath(str(folder_b))
        assert window._folder_path == expected_path, (
            f"Expected _folder_path={expected_path!r}, got {window._folder_path!r}"
        )

        header_text = window._file_tree._header.text()
        assert "FOLDER_B" in header_text.upper(), (
            f"Expected header to contain 'FOLDER_B', got {header_text!r}"
        )

        window.close()
        qapp.processEvents()


# ===========================================================================
# C11 — ControlBar open-menu signals
# ===========================================================================

class TestC11ControlBarSignals:
    def test_control_bar_open_menu_signals(self, qapp):
        """
        C11: Triggering each action in the Open button's menu emits the
        correct ControlBar signal and only that signal.

        'Open File...'   → open_clicked
        'Open Folder...' → open_folder_clicked
        """
        bar = ControlBar()
        qapp.processEvents()

        open_file_spy = Mock()
        open_folder_spy = Mock()
        bar.open_clicked.connect(open_file_spy)
        bar.open_folder_clicked.connect(open_folder_spy)

        actions = bar._open_btn.menu().actions()
        assert len(actions) >= 2, (
            f"Expected at least 2 actions in Open menu, found {len(actions)}"
        )
        open_file_action = actions[0]    # "Open File...\tCtrl+O"
        open_folder_action = actions[1]  # "Open Folder...\tCtrl+Shift+O"

        open_file_action.trigger()
        qapp.processEvents()
        assert open_file_spy.call_count == 1, (
            "open_clicked must fire exactly once for 'Open File...'"
        )
        assert open_folder_spy.call_count == 0, (
            "open_folder_clicked must not fire when 'Open File...' is triggered"
        )

        open_folder_action.trigger()
        qapp.processEvents()
        assert open_folder_spy.call_count == 1, (
            "open_folder_clicked must fire exactly once for 'Open Folder...'"
        )
        assert open_file_spy.call_count == 1, (
            "open_clicked must not fire when 'Open Folder...' is triggered"
        )


# ===========================================================================
# Suite D — Integration with Probe Persistence
# ===========================================================================

# ---------------------------------------------------------------------------
# D-level helpers and fixtures
# ---------------------------------------------------------------------------

def _x_anchor() -> ProbeAnchor:
    """
    Build a ProbeAnchor for 'x' at line 9 of main_entry.py.

    main_entry.py line 9:  ``    x = compute(5)``
    Column 4 (0-indexed) is where 'x' sits.
    """
    return ProbeAnchor(
        file=os.path.abspath(MAIN_ENTRY),
        line=9,
        col=4,
        symbol="x",
        func="main",
        is_assignment=True,
    )


@pytest.fixture
def cleanup_both_sidecars():
    """Remove sidecars for loop_script.py and main_entry.py before/after."""
    sidecars = [get_sidecar_path(LOOP_SCRIPT), get_sidecar_path(MAIN_ENTRY)]
    for s in sidecars:
        if s.exists():
            s.unlink()
    yield
    for s in sidecars:
        if s.exists():
            s.unlink()


# ===========================================================================
# D1 — Sidecar roundtrip across two files
# ===========================================================================

def test_sidecar_roundtrip_across_files(win, qapp, cleanup_both_sidecars):
    """
    D1: Probes added to file A are saved when switching to file B, and
    restored when switching back.  The same roundtrip works for file B.

    Sequence:
        1. Load folder  → select A → add 'y' probe
        2. Select B     → sidecar for A must be written
        3. Add 'x' probe to B
        4. Select A     → sidecar for B must be written;  'y' probe restored
        5. Select B     → 'x' probe restored
    """
    win._load_folder(FOLDER_TEST_DIR)
    _pev(qapp)

    # ── Step 1: File A — add a probe ─────────────────────────────────────────
    win._on_file_tree_selected(LOOP_SCRIPT)
    _pev(qapp)
    win._on_probe_requested(_y_anchor())
    _pev(qapp)
    assert len(win._probe_panels) == 1, "Precondition: 1 probe on file A"

    # ── Step 2: Switch to File B — A's sidecar must be written ───────────────
    win._on_file_tree_selected(MAIN_ENTRY)
    _pev(qapp)
    assert get_sidecar_path(LOOP_SCRIPT).exists(), (
        "Switching away from file A must create its sidecar"
    )

    # ── Step 3: File B — add a different probe ────────────────────────────────
    win._on_probe_requested(_x_anchor())
    _pev(qapp)
    assert len(win._probe_panels) == 1, "Precondition: 1 probe on file B"

    # ── Step 4: Switch back to File A — B's sidecar written; A restored ───────
    win._on_file_tree_selected(LOOP_SCRIPT)
    _pev(qapp)
    assert get_sidecar_path(MAIN_ENTRY).exists(), (
        "Switching away from file B must create its sidecar"
    )
    assert len(win._probe_panels) > 0, (
        "File A's probe must be restored from sidecar on switch-back"
    )
    restored_symbols_a = {a.symbol for a in win._probe_panels}
    assert "y" in restored_symbols_a, (
        f"Expected 'y' probe restored for file A, got: {restored_symbols_a}"
    )

    # ── Step 5: Switch back to File B — B's probe must also be restored ───────
    win._on_file_tree_selected(MAIN_ENTRY)
    _pev(qapp)
    assert len(win._probe_panels) > 0, (
        "File B's probe must be restored from sidecar on switch-back"
    )
    restored_symbols_b = {a.symbol for a in win._probe_panels}
    assert "x" in restored_symbols_b, (
        f"Expected 'x' probe restored for file B, got: {restored_symbols_b}"
    )


# ===========================================================================
# D2 — No sidecar created when switching away with no probes
# ===========================================================================

def test_sidecar_not_created_if_no_probes(win, qapp, cleanup_sidecar):
    """
    D2: Switching away from a file that has no active probes or watches must
    not create a .pyprobe sidecar file.
    """
    win._load_folder(FOLDER_TEST_DIR)
    win._on_file_tree_selected(LOOP_SCRIPT)
    _pev(qapp)

    # No probes added — just switch to trigger _save_probe_settings()
    win._on_file_tree_selected(MAIN_ENTRY)
    _pev(qapp)

    sidecar = get_sidecar_path(LOOP_SCRIPT)
    assert not sidecar.exists(), (
        "No .pyprobe sidecar should be created when switching away from a "
        "file with no active probes or watches"
    )


# ===========================================================================
# D3 — Scalar watches cleared on file switch
# ===========================================================================

def test_watch_scalars_cleared_on_file_switch(win, qapp, cleanup_sidecar):
    """
    D3: The scalar watch sidebar must be empty after switching to a different
    file, even when a scalar watch was active on the previous file.

    cleanup_sidecar handles the sidecar that _save_probe_settings() creates
    for the watch entry.
    """
    win._load_folder(FOLDER_TEST_DIR)
    win._on_file_tree_selected(LOOP_SCRIPT)
    _pev(qapp)

    win._scalar_watch_sidebar.add_scalar(_y_anchor(), QColor("#00ffff"))
    _pev(qapp)
    assert win._scalar_watch_sidebar._scalars, (
        "Precondition: scalar sidebar must have an entry after add_scalar"
    )

    # Switch to a different file — _clear_all_probes must empty the sidebar
    win._on_file_tree_selected(MAIN_ENTRY)
    _pev(qapp)

    assert win._scalar_watch_sidebar._scalars == {}, (
        "Scalar watch sidebar must be empty after switching to a different file"
    )
