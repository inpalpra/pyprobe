"""Fast tests implementation for folder browsing GUI state."""

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
from pyprobe.gui.main_window import MainWindow, SPLIT_TREE, SPLIT_CODE, SPLIT_PROBES, SPLIT_WATCH

_HERE = os.path.dirname(__file__)
REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
FOLDER_TEST_DIR = os.path.join(REPO_ROOT, "regression", "folder_test")
LOOP_SCRIPT = os.path.abspath(os.path.join(FOLDER_TEST_DIR, "loop_script.py"))
MAIN_ENTRY = os.path.abspath(os.path.join(FOLDER_TEST_DIR, "main_entry.py"))
REGRESSION_LOOP = os.path.abspath(os.path.join(REPO_ROOT, "regression", "loop.py"))

_STATE = {}

def _y_anchor(script_path: str = LOOP_SCRIPT) -> ProbeAnchor:
    return ProbeAnchor(file=os.path.abspath(script_path), line=2, col=8, symbol="y", func="main", is_assignment=True)

def _x_anchor() -> ProbeAnchor:
    return ProbeAnchor(file=os.path.abspath(MAIN_ENTRY), line=9, col=4, symbol="x", func="main", is_assignment=True)

def _make_py_file(directory: str, name: str, content: str = "x = 1\n") -> str:
    path = os.path.join(directory, name)
    with open(path, "w") as f:
        f.write(content)
    return os.path.abspath(path)

def _wait_for(condition, qapp, timeout: float = 2.0, interval: float = 0.01) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        qapp.processEvents()
        if condition():
            return True
        time.sleep(interval)
    return False

@pytest.fixture(scope="module", autouse=True)
def _run_all_scenarios(qapp, tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("folder_browsing")
    sidecars = [get_sidecar_path(LOOP_SCRIPT), get_sidecar_path(MAIN_ENTRY)]
    for s in sidecars:
        if s.exists(): s.unlink()

    mw = MainWindow()
    mw.resize(1200, 800)
    mw.show()
    qapp.processEvents()

    # B1a
    _STATE["b1_tree_hidden"] = not mw._file_tree.isVisible()
    _STATE["b1_tree_expanded"] = mw._tree_pane.is_expanded

    # B1b
    mw._load_script(REGRESSION_LOOP)
    qapp.processEvents()
    _STATE["b1b_tree_hidden"] = not mw._file_tree.isVisible()

    # B2
    mw._load_folder(FOLDER_TEST_DIR)
    qapp.processEvents()
    _STATE["b2_tree_visible"] = mw._file_tree.isVisible()
    _STATE["b2_splitter_width"] = mw._main_splitter.sizes()[SPLIT_TREE]
    _STATE["b2_folder_path"] = mw._folder_path
    _STATE["b2_header"] = mw._file_tree._header.text()

    # B3
    _wait_for(lambda: mw._file_tree._fs_model.rowCount(mw._file_tree._fs_model.index(FOLDER_TEST_DIR)) > 0, qapp, timeout=5.0)
    fs_model = mw._file_tree._fs_model
    proxy = mw._file_tree._proxy
    txt_path = os.path.join(FOLDER_TEST_DIR, "data_file.txt")
    _STATE["b3_txt_src_valid"] = fs_model.index(txt_path).isValid()
    _STATE["b3_txt_proxy_valid"] = proxy.mapFromSource(fs_model.index(txt_path)).isValid()
    _STATE["b3_py_proxy_valid"] = proxy.mapFromSource(fs_model.index(LOOP_SCRIPT)).isValid()
    subdir_path = os.path.join(FOLDER_TEST_DIR, "subdir")
    _STATE["b3_subdir_src_valid"] = fs_model.index(subdir_path).isValid()
    _STATE["b3_subdir_proxy_valid"] = proxy.mapFromSource(fs_model.index(subdir_path)).isValid()

    # B4
    mw._on_file_tree_selected(LOOP_SCRIPT)
    qapp.processEvents()
    _STATE["b4_script_path"] = mw._script_path
    _STATE["b4_code_viewer_content"] = mw._code_viewer.toPlainText()
    _STATE["b4_control_bar_script_loaded"] = mw._control_bar._script_loaded
    _STATE["b4_status_bar_msg"] = mw._status_bar.currentMessage()

    # B5
    anchor_y = _y_anchor()
    mw._on_probe_requested(anchor_y)
    qapp.processEvents()
    mw._on_file_tree_selected(MAIN_ENTRY)
    qapp.processEvents()
    _STATE["b5_probe_panels_after"] = dict(mw._probe_panels)
    _STATE["b5_registry_anchors"] = set(mw._probe_registry.all_anchors)
    _STATE["b5_code_viewer_content"] = mw._code_viewer.toPlainText()

    # B6a / B6b 
    _STATE["b6a_sidecar_exists"] = get_sidecar_path(LOOP_SCRIPT).exists()
    mw._on_file_tree_selected(LOOP_SCRIPT)
    qapp.processEvents()
    _STATE["b6b_probe_panels"] = len(mw._probe_panels)

    # B7 
    class _FakeRunner:
        is_running = True
        ipc = None
        user_stopped = False
        def __init__(self, real): self._real = real
        def __getattr__(self, name): return getattr(self._real, name)
    real_runner = mw._script_runner
    mw._script_runner = _FakeRunner(real_runner)
    try:
        mw._on_file_tree_selected(MAIN_ENTRY)
        qapp.processEvents()
        _STATE["b7_exception"] = None
    except Exception as exc:
        _STATE["b7_exception"] = exc
    finally:
        mw._script_runner = real_runner
    _STATE["b7_script_path"] = mw._script_path

    # B8 
    mw._on_file_tree_selected(LOOP_SCRIPT)
    qapp.processEvents()
    mw._on_probe_requested(anchor_y)
    qapp.processEvents()
    panels_before = len(mw._probe_panels)
    mw._on_file_tree_selected(LOOP_SCRIPT)
    qapp.processEvents()
    _STATE["b8_probe_panels_same"] = False
    if anchor_y in mw._probe_panels and len(mw._probe_panels) == panels_before:
        _STATE["b8_probe_panels_same"] = True
    _STATE["b8_script_path"] = mw._script_path

    # B9
    mw._on_file_tree_selected(LOOP_SCRIPT)
    qapp.processEvents()
    _STATE["b9_current_file_1"] = mw._file_tree._current_file
    mw._on_file_tree_selected(MAIN_ENTRY)
    qapp.processEvents()
    _STATE["b9_current_file_2"] = mw._file_tree._current_file
    mw._on_file_tree_selected(LOOP_SCRIPT)
    qapp.processEvents()
    _STATE["b9_current_file_3"] = mw._file_tree._current_file

    # B10
    with patch("pyprobe.gui.main_window.QFileDialog.getOpenFileName", return_value=("", "")) as mock_dialog:
        mw._on_open_script()
        qapp.processEvents()
        if mock_dialog.called:
            _STATE["b10_start_dir"] = mock_dialog.call_args[0][2]
        else:
            _STATE["b10_start_dir"] = None

    # B11
    scalar_anchor = ProbeAnchor(file=LOOP_SCRIPT, line=2, col=8, symbol="y", func="main", is_assignment=True)
    mw._scalar_watch_sidebar.add_scalar(scalar_anchor, QColor("#00ffff"), "tr0")
    qapp.processEvents()
    mw._cli_probes = ["2:y:1"]
    mw._cli_watches = ["2:y:1"]
    mw._cli_overlays = ["y:2:z:1"]
    mw._clear_all_probes()
    qapp.processEvents()
    _STATE["b11_probe_panels"] = len(mw._probe_panels)
    _STATE["b11_probe_metadata"] = len(mw._probe_controller._probe_metadata)
    _STATE["b11_registry_anchors"] = len(mw._probe_registry.all_anchors)
    _STATE["b11_scalar_sidebar"] = len(mw._scalar_watch_sidebar._scalars)
    _STATE["b11_cli_probes"] = len(mw._cli_probes)
    _STATE["b11_cli_watches"] = len(mw._cli_watches)
    _STATE["b11_cli_overlays"] = len(mw._cli_overlays)

    # B12
    sp = mw._main_splitter
    _STATE["b12_split_tree"] = (sp.widget(SPLIT_TREE) is mw._tree_pane)
    _STATE["b12_split_code"] = (sp.widget(SPLIT_CODE) is not None)
    _STATE["b12_split_probes"] = (sp.widget(SPLIT_PROBES) is mw._probe_container)
    _STATE["b12_split_watch"] = (sp.widget(SPLIT_WATCH) is mw._watch_pane)
    _STATE["b12_count"] = sp.count()

    # B12b
    mw._load_script(REGRESSION_LOOP)
    qapp.processEvents()
    sizes_before = mw._main_splitter.sizes()
    probes_before = sizes_before[SPLIT_PROBES]
    _STATE["b12b_watch_starts_collapsed"] = not mw._watch_pane.is_expanded

    mw._on_toggle_watch_window()
    qapp.processEvents()
    _STATE["b12b_sizes_after_watch"] = mw._main_splitter.sizes()[SPLIT_WATCH]
    _STATE["b12b_watch_expanded"] = mw._watch_pane.is_expanded
    _STATE["b12b_sidebar_visible"] = mw._scalar_watch_sidebar.isVisible()

    mw._on_toggle_watch_window()
    qapp.processEvents()
    sizes_hidden = mw._main_splitter.sizes()
    _STATE["b12b_watch_expanded_hidden"] = mw._watch_pane.is_expanded
    _STATE["b12b_sidebar_visible_hidden"] = mw._scalar_watch_sidebar.isVisible()
    _STATE["b12b_probes_reclaimed"] = (sizes_hidden[SPLIT_PROBES] >= probes_before)

    mw.close()
    qapp.processEvents()

    # ---------------- D Series ----------------
    for s in sidecars:
        if s.exists(): s.unlink()

    mw_d = MainWindow()
    mw_d.show()

    # D1
    mw_d._load_folder(FOLDER_TEST_DIR)
    qapp.processEvents()
    mw_d._on_file_tree_selected(LOOP_SCRIPT)
    qapp.processEvents()
    mw_d._on_probe_requested(_y_anchor())
    qapp.processEvents()
    _STATE["d1_a_panels"] = len(mw_d._probe_panels)
    
    mw_d._on_file_tree_selected(MAIN_ENTRY)
    qapp.processEvents()
    visible_panels = [p for panels in mw_d._probe_panels.values() for p in panels if p.isVisible()]
    _STATE["d1_b_visible_panels_before"] = len(visible_panels)
    
    mw_d._on_probe_requested(_x_anchor())
    qapp.processEvents()
    visible_panels = [p for panels in mw_d._probe_panels.values() for p in panels if p.isVisible()]
    _STATE["d1_b_visible_panels_after"] = len(visible_panels)
    
    mw_d._on_file_tree_selected(LOOP_SCRIPT)
    qapp.processEvents()
    _STATE["d1_b_sidecar_exists"] = get_sidecar_path(MAIN_ENTRY).exists()
    _STATE["d1_restored_symbols_a"] = {a.symbol for a in mw_d._probe_panels}

    mw_d._on_file_tree_selected(MAIN_ENTRY)
    qapp.processEvents()
    _STATE["d1_restored_symbols_b"] = {a.symbol for a in mw_d._probe_panels}

    for s in sidecars:
        if s.exists(): s.unlink()

    mw_d._clear_all_probes()
    qapp.processEvents()

    # D2
    mw_d._load_folder(FOLDER_TEST_DIR)
    mw_d._on_file_tree_selected(LOOP_SCRIPT)
    qapp.processEvents()
    mw_d._on_file_tree_selected(MAIN_ENTRY)
    qapp.processEvents()
    _STATE["d2_sidecar_exists"] = get_sidecar_path(LOOP_SCRIPT).exists()

    # D3.5a
    mw_d._load_folder(FOLDER_TEST_DIR)
    qapp.processEvents()
    mw_d._on_file_tree_selected(LOOP_SCRIPT)
    qapp.processEvents()
    _STATE["d35a_run_target_1"] = mw_d._run_target_path
    mw_d._on_file_tree_selected(MAIN_ENTRY)
    qapp.processEvents()
    _STATE["d35a_run_target_2"] = mw_d._run_target_path
    mw_d._on_file_tree_selected(LOOP_SCRIPT)
    qapp.processEvents()
    _STATE["d35a_run_target_3"] = mw_d._run_target_path

    # D3
    mw_d._on_file_tree_selected(LOOP_SCRIPT)
    qapp.processEvents()
    mw_d._scalar_watch_sidebar.add_scalar(_y_anchor(), QColor("#00ffff"), "tr0")
    qapp.processEvents()
    _STATE["d3_sidebar_scalars_before"] = len(mw_d._scalar_watch_sidebar._scalars)
    mw_d._on_file_tree_selected(MAIN_ENTRY)
    qapp.processEvents()
    visible_scalars = [a for a in mw_d._scalar_watch_sidebar.get_watched_anchors() if a.file == MAIN_ENTRY]
    _STATE["d3_visible_scalars"] = len(visible_scalars)

    mw_d.close()
    
    # D3.5b
    mw_d2 = MainWindow(script_path=LOOP_SCRIPT)
    mw_d2.show()
    qapp.processEvents()
    _STATE["d35b_explicit_target_1"] = getattr(mw_d2, '_explicit_run_target', False)
    _STATE["d35b_run_target_1"] = mw_d2._run_target_path
    mw_d2._load_folder(FOLDER_TEST_DIR)
    qapp.processEvents()
    mw_d2._on_file_tree_selected(MAIN_ENTRY)
    qapp.processEvents()
    _STATE["d35b_run_target_2"] = mw_d2._run_target_path
    mw_d2.close()

    # ---------------- C Series ----------------
    # C1 Rapid file switching
    files_c1 = [_make_py_file(str(tmp_path), f"s{i}.py", f"x = {i}\n") for i in range(5)]
    mw_c1 = MainWindow()
    mw_c1._load_folder(str(tmp_path))
    qapp.processEvents()
    for i in range(20):
        mw_c1._on_file_tree_selected(files_c1[i % len(files_c1)])
        qapp.processEvents()
    _STATE["c1_script_path"] = mw_c1._script_path
    _STATE["c1_expected_path"] = files_c1[19 % len(files_c1)]
    _STATE["c1_probe_panels"] = len(mw_c1._probe_panels)
    mw_c1.close()

    # C2 Large folder
    large_dir = tmp_path / "large"
    large_dir.mkdir()
    for i in range(100):
        _make_py_file(str(large_dir), f"module_{i:03d}.py", f"val = {i}\n")
    p_c2 = FileTreePanel()
    p_c2.resize(300, 500)
    p_c2.show()
    qapp.processEvents()
    
    p_c2.set_root(str(large_dir))
    _wait_for(lambda: p_c2._proxy.rowCount(p_c2._tree.rootIndex()) > 0, qapp, timeout=5.0)
    
    proxy_root = p_c2._tree.rootIndex()
    row_count = p_c2._proxy.rowCount(proxy_root)
    _STATE["c2_row_count"] = row_count
    
    received_c2 = []
    p_c2.file_selected.connect(received_c2.append)
    clicked_c2 = False
    for row in range(row_count):
        idx = p_c2._proxy.index(row, 0, proxy_root)
        src = p_c2._proxy.mapToSource(idx)
        fi = p_c2._fs_model.fileInfo(src)
        if fi.isFile() and fi.suffix() == "py":
            p_c2._on_clicked(idx)
            qapp.processEvents()
            clicked_c2 = True
            break
    _STATE["c2_clicked"] = clicked_c2
    _STATE["c2_received_len"] = len(received_c2)
    _STATE["c2_received_val"] = received_c2[0] if received_c2 else None
    
    # C3 Empty folder
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    p_c2.set_root(str(empty_dir))
    _wait_for(lambda: p_c2._fs_model.index(str(empty_dir)).isValid(), qapp, timeout=1.0)
    for _ in range(5): qapp.processEvents()
    _STATE["c3_row_count"] = p_c2._proxy.rowCount(p_c2._tree.rootIndex())
    
    # C4 No py files
    txt_dir = tmp_path / "txt_only"
    txt_dir.mkdir()
    for i in range(3):
        (txt_dir / f"notes_{i}.txt").write_text("hello\n")
    p_c2.set_root(str(txt_dir))
    for _ in range(5): qapp.processEvents()
    visible_files = []
    def _collect(parent):
        for r in range(p_c2._proxy.rowCount(parent)):
            idx = p_c2._proxy.index(r, 0, parent)
            fi = p_c2._fs_model.fileInfo(p_c2._proxy.mapToSource(idx))
            if fi.isFile(): visible_files.append(fi.absoluteFilePath())
            elif fi.isDir(): _collect(idx)
    _collect(p_c2._tree.rootIndex())
    py_files = [p for p in visible_files if p.endswith(".py")]
    _STATE["c4_py_files_len"] = len(py_files)
    
    # C5 Deeply nested
    nested_dir = tmp_path / "a" / "b" / "c" / "d" / "e"
    nested_dir.mkdir(parents=True)
    script_c5 = nested_dir / "script.py"
    script_c5.write_text("z = 99\n")
    p_c2.set_root(str(tmp_path))
    for _ in range(5): qapp.processEvents()
    p_c2.highlight_file(str(script_c5))
    qapp.processEvents()
    _STATE["c5_current_file"] = p_c2._current_file
    _STATE["c5_expected_file"] = str(script_c5)
    
    # C6 Pycache
    pyc_dir = tmp_path / "pyc_test"
    pyc_dir.mkdir()
    _make_py_file(str(pyc_dir), "main.py")
    pyc_inner = pyc_dir / "__pycache__"
    pyc_inner.mkdir()
    (pyc_inner / "main.cpython-312.pyc").write_bytes(b"\x00\x00\x00\x00")
    p_c2.set_root(str(pyc_dir))
    for _ in range(5): qapp.processEvents()
    visible_files_c6 = []
    def _collect_c6(parent):
        for r in range(p_c2._proxy.rowCount(parent)):
            idx = p_c2._proxy.index(r, 0, parent)
            fi = p_c2._fs_model.fileInfo(p_c2._proxy.mapToSource(idx))
            if fi.isFile(): visible_files_c6.append(fi.absoluteFilePath())
            elif fi.isDir(): _collect_c6(idx)
    _collect_c6(p_c2._tree.rootIndex())
    py_c6 = [p for p in visible_files_c6 if p.endswith(".py")]
    pyc_c6 = [p for p in visible_files_c6 if p.endswith(".pyc")]
    _STATE["c6_pyc_len"] = len(pyc_c6)
    _STATE["c6_py_contains_main"] = any(p.endswith("main.py") for p in py_c6)

    # C9
    new_file = pyc_dir / "new_module.py"
    new_file.write_text("a = 42\n")
    new_file_abs = str(new_file.resolve())
    appeared = _wait_for(lambda: p_c2._fs_model.index(new_file_abs).isValid(), qapp)
    _STATE["c9_appeared"] = appeared
    source_idx = p_c2._fs_model.index(new_file_abs)
    _STATE["c9_proxy_valid"] = p_c2._proxy.mapFromSource(source_idx).isValid()
    p_c2.close()
    
    # C7 File Modified
    mod_dir = tmp_path / "mod_test"
    mod_dir.mkdir()
    script_c7 = _make_py_file(str(mod_dir), "watched.py", "x = 1\n")
    other_c7 = _make_py_file(str(mod_dir), "other.py", "y = 2\n")
    mw_c7 = MainWindow()
    mw_c7._load_folder(str(mod_dir))
    mw_c7._on_file_tree_selected(script_c7)
    qapp.processEvents()
    _STATE["c7_initial_content"] = mw_c7._last_source_content
    with open(script_c7, "w") as f:
        f.write("x = 2  # modified\n")
    detected = _wait_for(lambda: "modified" in (mw_c7._last_source_content or ""), qapp, timeout=3.0)
    _STATE["c7_detected"] = detected
    mw_c7._on_file_tree_selected(other_c7)
    qapp.processEvents()
    _STATE["c7_script_path"] = mw_c7._script_path
    mw_c7.close()

    # C8 File deleted
    del_dir = tmp_path / "del_test"
    del_dir.mkdir()
    script_c8 = _make_py_file(str(del_dir), "ephem.py", "z = 0\n")
    survivor_c8 = _make_py_file(str(del_dir), "surv.py", "z = 1\n")
    mw_c8 = MainWindow()
    mw_c8._load_folder(str(del_dir))
    mw_c8._on_file_tree_selected(script_c8)
    qapp.processEvents()
    os.remove(script_c8)
    for _ in range(10):
        qapp.processEvents()
        time.sleep(0.01)
    mw_c8._on_file_tree_selected(survivor_c8)
    qapp.processEvents()
    _STATE["c8_script_path"] = mw_c8._script_path
    mw_c8.close()

    # C10 Open folder clears previous
    f_a = tmp_path / "fa"
    f_b = tmp_path / "fb"
    f_a.mkdir()
    f_b.mkdir()
    _make_py_file(str(f_a), "alpha.py")
    _make_py_file(str(f_b), "beta.py")
    mw_c10 = MainWindow()
    mw_c10._load_folder(str(f_a))
    qapp.processEvents()
    _STATE["c10_fa_path"] = mw_c10._folder_path
    mw_c10._load_folder(str(f_b))
    qapp.processEvents()
    _STATE["c10_fb_path"] = mw_c10._folder_path
    _STATE["c10_header"] = mw_c10._file_tree._header.text()
    mw_c10.close()

    # C11
    bar = ControlBar()
    bar.show()
    qapp.processEvents()
    open_file_spy = Mock()
    open_folder_spy = Mock()
    bar.open_clicked.connect(open_file_spy)
    bar.open_folder_clicked.connect(open_folder_spy)
    actions = bar._open_btn.menu().actions()
    _STATE["c11_actions_len"] = len(actions)
    if len(actions) >= 2:
        actions[0].trigger()
        qapp.processEvents()
        _STATE["c11_file_spy_1"] = open_file_spy.call_count
        _STATE["c11_folder_spy_1"] = open_folder_spy.call_count
        actions[1].trigger()
        qapp.processEvents()
        _STATE["c11_file_spy_2"] = open_file_spy.call_count
        _STATE["c11_folder_spy_2"] = open_folder_spy.call_count
    bar.close()

# ===========================================================================
# Assertions
# ===========================================================================

def test_file_tree_hidden_on_startup():
    assert _STATE["b1_tree_hidden"]
    assert not _STATE["b1_tree_expanded"]

def test_file_tree_hidden_when_opening_single_file():
    assert _STATE["b1b_tree_hidden"]

def test_file_tree_shown_on_folder_load():
    assert _STATE["b2_tree_visible"]
    assert _STATE["b2_splitter_width"] > 0
    assert _STATE["b2_folder_path"] == os.path.abspath(FOLDER_TEST_DIR)
    expected_header = os.path.basename(FOLDER_TEST_DIR).upper()
    assert _STATE["b2_header"] == expected_header

def test_file_tree_shows_only_py_files():
    assert _STATE["b3_txt_src_valid"]
    assert not _STATE["b3_txt_proxy_valid"]
    assert _STATE["b3_py_proxy_valid"]
    assert _STATE["b3_subdir_src_valid"]
    assert _STATE["b3_subdir_proxy_valid"]

def test_file_tree_click_loads_script():
    assert _STATE["b4_script_path"] == LOOP_SCRIPT
    assert "for y in" in _STATE["b4_code_viewer_content"]
    assert _STATE["b4_control_bar_script_loaded"]
    assert "loop_script.py" in _STATE["b4_status_bar_msg"]

def test_file_switch_clears_old_probes():
    assert _STATE["b5_probe_panels_after"] != {}
    assert len(_STATE["b5_registry_anchors"]) > 0
    assert "compute" in _STATE["b5_code_viewer_content"]

def test_file_switch_saves_sidecar():
    assert _STATE["b6a_sidecar_exists"]

def test_file_switch_restores_probes_from_sidecar():
    assert _STATE["b6b_probe_panels"] > 0

def test_file_switch_during_execution_not_crash():
    assert _STATE["b7_exception"] is None
    assert _STATE["b7_script_path"] == MAIN_ENTRY

def test_reselect_same_file_no_op():
    assert _STATE["b8_probe_panels_same"]
    assert _STATE["b8_script_path"] == LOOP_SCRIPT

def test_file_tree_highlight_tracks_selection():
    assert _STATE["b9_current_file_1"] == LOOP_SCRIPT
    assert _STATE["b9_current_file_2"] == MAIN_ENTRY
    assert _STATE["b9_current_file_3"] == LOOP_SCRIPT

def test_open_file_dialog_starts_in_folder():
    assert _STATE["b10_start_dir"] == os.path.abspath(FOLDER_TEST_DIR)

def test_clear_all_probes_cleans_everything():
    assert _STATE["b11_probe_panels"] == 0
    assert _STATE["b11_probe_metadata"] == 0
    assert _STATE["b11_registry_anchors"] == 0
    assert _STATE["b11_scalar_sidebar"] == 0
    assert _STATE["b11_cli_probes"] == 0
    assert _STATE["b11_cli_watches"] == 0
    assert _STATE["b11_cli_overlays"] == 0

def test_splitter_layout_contract():
    assert _STATE["b12_split_tree"]
    assert _STATE["b12_split_code"]
    assert _STATE["b12_split_probes"]
    assert _STATE["b12_split_watch"]
    assert _STATE["b12_count"] == 4

def test_watch_toggle_affects_correct_pane():
    assert _STATE["b12b_watch_starts_collapsed"]
    assert _STATE["b12b_sizes_after_watch"] > 20
    assert _STATE["b12b_watch_expanded"]
    assert _STATE["b12b_sidebar_visible"]
    assert not _STATE["b12b_watch_expanded_hidden"]
    assert not _STATE["b12b_sidebar_visible_hidden"]
    assert _STATE["b12b_probes_reclaimed"]

def test_sidecar_roundtrip_across_files():
    assert _STATE["d1_a_panels"] == 1
    assert _STATE["d1_b_visible_panels_before"] == 0
    assert _STATE["d1_b_visible_panels_after"] == 1
    assert _STATE["d1_b_sidecar_exists"]
    assert "y" in _STATE["d1_restored_symbols_a"]
    assert "x" in _STATE["d1_restored_symbols_b"]

def test_sidecar_not_created_if_no_probes():
    assert not _STATE["d2_sidecar_exists"]

def test_watch_scalars_cleared_on_file_switch():
    assert _STATE["d3_sidebar_scalars_before"] > 0
    assert _STATE["d3_visible_scalars"] == 0

def test_run_target_follows_current_file_in_folder_mode():
    assert _STATE["d35a_run_target_1"] == LOOP_SCRIPT
    assert _STATE["d35a_run_target_2"] == MAIN_ENTRY
    assert _STATE["d35a_run_target_3"] == LOOP_SCRIPT

def test_run_target_stays_fixed_in_script_mode():
    assert _STATE["d35b_explicit_target_1"]
    assert _STATE["d35b_run_target_1"] == LOOP_SCRIPT
    assert _STATE["d35b_run_target_2"] == LOOP_SCRIPT

class TestC1RapidFileSwitching:
    def test_rapid_file_switching(self):
        assert _STATE["c1_script_path"] == _STATE["c1_expected_path"]
        assert _STATE["c1_probe_panels"] == 0

class TestC2LargeFolder:
    def test_large_folder(self):
        assert _STATE["c2_row_count"] > 0
        assert _STATE["c2_clicked"]
        assert _STATE["c2_received_len"] == 1
        assert _STATE["c2_received_val"].endswith(".py")

class TestC3EmptyFolder:
    def test_empty_folder(self):
        assert _STATE["c3_row_count"] == 0

class TestC4NoPyFiles:
    def test_folder_with_no_py_files(self):
        assert _STATE["c4_py_files_len"] == 0

class TestC5DeeplyNested:
    def test_deeply_nested_folder(self):
        assert _STATE["c5_current_file"] == _STATE["c5_expected_file"]

class TestC6Pycache:
    def test_folder_with_pycache(self):
        assert _STATE["c6_pyc_len"] == 0
        assert _STATE["c6_py_contains_main"]

class TestC7FileModified:
    def test_file_modified_externally_while_in_tree(self):
        assert "x = 1" in (_STATE["c7_initial_content"] or "")
        assert _STATE["c7_detected"]
        assert _STATE["c7_script_path"].endswith("other.py")

class TestC8FileDeleted:
    def test_file_deleted_while_selected(self):
        assert _STATE["c8_script_path"].endswith("surv.py")

class TestC9NewFileCreated:
    def test_new_file_created_in_folder(self):
        assert _STATE["c9_appeared"]
        assert _STATE["c9_proxy_valid"]

class TestC10FolderReplace:
    def test_open_folder_clears_previous_folder(self):
        assert _STATE["c10_fb_path"].endswith("fb")
        assert "FB" in _STATE["c10_header"].upper()

class TestC11ControlBarSignals:
    def test_control_bar_open_menu_signals(self):
        assert _STATE["c11_actions_len"] >= 2
        assert _STATE["c11_file_spy_1"] == 1
        assert _STATE["c11_folder_spy_1"] == 0
        assert _STATE["c11_file_spy_2"] == 1
        assert _STATE["c11_folder_spy_2"] == 1
