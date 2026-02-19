# Folder Browsing — Stress Test Plan

## Testing Strategy

Use the same **subprocess-based E2E pattern** as existing tests (`test_e2e_capture_pipeline.py`). The GUI runs as a real subprocess with `--auto-run --auto-quit`, and we parse `PLOT_DATA:` JSON output + log messages.

For folder-specific flows, we'll also need **in-process pytest-qt tests** to verify GUI state (file tree visibility, splitter sizing, file switching, probe cleanup) since those aren't observable via subprocess stdout.

---

## Test Fixtures

### Regression Folder: `regression/folder_test/`

A dedicated folder with multiple `.py` scripts designed for deterministic probing:

```
regression/folder_test/
├── main_entry.py        # Entry point: imports helper, x = compute(5) → x=25
├── helper.py            # def compute(n): result = n * n; return result
├── loop_script.py       # Standalone: y in [10, 20, 30]
├── empty_script.py      # No-op script (edge case)
├── data_file.txt        # Non-.py file (should be filtered out of tree)
└── subdir/
    └── nested_script.py # z = 99 (tests nested folder display)
```

---

## Test Suite A: Subprocess E2E (folder open via CLI)

### A1. `test_open_folder_cli_then_file`
**Scenario:** `python -m pyprobe examples/` — open folder, no file loaded.
**Assert:** Clean exit (returncode == 0 with `--auto-quit-timeout 3`). No crash on startup with folder-only arg.

### A2. `test_open_folder_with_probe_ignored`
**Scenario:** `python -m pyprobe --probe 4:x:1 examples/` — folder + probe args.
**Assert:** Probes are silently ignored (no file loaded yet to attach to). No crash. Clean exit.

### A3. `test_open_file_in_folder_run_probe`
**Scenario:** Open `regression/folder_test/loop_script.py` directly (not folder). Standard probe flow.
**Assert:** `PLOT_DATA` for `y` = `[10.0, 20.0, 30.0]`. Baseline to compare against folder flow.

### A4. `test_folder_preserves_file_behavior`
**Scenario:** Open same file from A3 but via normal file arg (current behavior).
**Assert:** Identical PLOT_DATA output to A3. Ensures folder feature didn't regress file-only flow.

---

## Test Suite B: In-Process pytest-qt (GUI state verification)

These tests create `MainWindow` in-process with `qapp`, manipulate widgets, and assert state.

### B1. `test_file_tree_hidden_on_startup`
**Setup:** `MainWindow(script_path="regression/loop.py")`
**Assert:** `_file_tree.isVisible() == False`. Splitter sizes[0] == 0.

### B2. `test_file_tree_shown_on_folder_load`
**Setup:** `MainWindow()` → `_load_folder("regression/folder_test/")`
**Assert:**
- `_file_tree.isVisible() == True`
- Splitter sizes[0] > 0 (tree has width)
- Header text matches folder name
- `_folder_path` is set

### B3. `test_file_tree_shows_only_py_files`
**Setup:** Load `regression/folder_test/` (which contains `.py` + `.txt` + subdir)
**Assert:**
- Iterate visible items in tree model
- All leaf items have `.py` suffix
- `data_file.txt` is NOT in the visible items
- `subdir/` IS visible (contains `.py` children)

### B4. `test_file_tree_click_loads_script`
**Setup:** Load folder → simulate click on `loop_script.py` in tree
**Assert:**
- `_script_path` == absolute path to `loop_script.py`
- `_code_viewer.toPlainText()` contains the script source
- `_control_bar._script_loaded == True`
- Status bar shows the filename

### B5. `test_file_switch_clears_old_probes`
**Setup:**
1. Load folder → select `loop_script.py` → add probe (via `_on_probe_requested`)
2. Select `main_entry.py` from tree
**Assert:**
- `_probe_panels` is empty after switch
- `_probe_registry.all_anchors` is empty
- `_code_viewer.toPlainText()` shows `main_entry.py` content
- CodeViewer has no active probe highlights

### B6. `test_file_switch_saves_sidecar`
**Setup:**
1. Load folder → select `loop_script.py` → add probe
2. Select `main_entry.py` from tree
**Assert:**
- `.pyprobe` sidecar exists for `loop_script.py` with saved probe
- After switching back to `loop_script.py`: probe is restored from sidecar

### B7. `test_file_switch_during_execution_not_crash`
**Setup:**
1. Load folder → select `loop_script.py` → start running
2. While running, select `main_entry.py` from tree
**Assert:**
- No crash / exception
- Behavior is defined (either blocks switch until stopped, or stops + switches)

### B8. `test_reselect_same_file_no_op`
**Setup:** Load folder → select `loop_script.py` → select `loop_script.py` again
**Assert:** `_on_file_tree_selected` returns early. No probe clearing. No churn.

### B9. `test_file_tree_highlight_tracks_selection`
**Setup:** Load folder → select file A → select file B → select file A again
**Assert:** Each time, `_file_tree._current_file` matches the selected file. Tree selection index matches.

### B10. `test_open_file_dialog_starts_in_folder`
**Setup:** Load folder → Open File... (check the start_dir passed to QFileDialog)
**Assert:** The file dialog opens in `_folder_path` (can mock `QFileDialog.getOpenFileName`).

### B11. `test_clear_all_probes_cleans_everything`
**Setup:** Create window with probes active → call `_clear_all_probes()`
**Assert:**
- `_probe_panels` == {}
- `_probe_controller._probe_metadata` == {}
- `_probe_registry.all_anchors` == set()
- `_scalar_watch_sidebar._scalars` == {}
- `_cli_probes` == [], `_cli_watches` == [], `_cli_overlays` == []

---

## Test Suite C: Stress / Edge Cases

### C1. `test_rapid_file_switching` (stress)
**Setup:** Load folder → click 20 different files in rapid succession (processEvents between each)
**Assert:** No crash. Final state matches last selected file. No memory leak (panel count stays 0).

### C2. `test_large_folder` (stress)
**Setup:** Create a temp folder with 100 `.py` files → load folder
**Assert:** Tree loads without freeze. All 100 files visible. Click on any file works.

### C3. `test_empty_folder`
**Setup:** Create empty temp folder → load folder
**Assert:** Tree shows empty state. No crash. Status bar indicates folder is empty or shows folder name.

### C4. `test_folder_with_no_py_files`
**Setup:** Create temp folder with only `.txt` files → load folder
**Assert:** Tree appears but has no selectable items. No crash.

### C5. `test_deeply_nested_folder`
**Setup:** Create `a/b/c/d/e/script.py` → load folder `a/`
**Assert:** Can navigate to and select `script.py` 5 levels deep.

### C6. `test_folder_with_pycache`
**Setup:** Folder with `__pycache__/`, `.pyc` files, normal `.py` files
**Assert:** `__pycache__` contents don't appear. Only `.py` source files shown.

### C7. `test_file_modified_externally_while_in_tree`
**Setup:** Load folder → select file → modify file on disk externally
**Assert:** `FileWatcher` fires. `AnchorMapper` updates probes. File tree still selectable.

### C8. `test_file_deleted_while_selected`
**Setup:** Load folder → select file → delete file on disk
**Assert:** Graceful handling. No crash. Tree updates (file disappears).

### C9. `test_new_file_created_in_folder`
**Setup:** Load folder → create new `.py` file on disk
**Assert:** `QFileSystemModel` auto-detects it. New file appears in tree.

### C10. `test_open_folder_clears_previous_folder`
**Setup:** Load folder A → load folder B
**Assert:** Tree shows folder B contents only. `_folder_path` == B.

### C11. `test_control_bar_open_menu_signals`
**Setup:** Create `ControlBar` → trigger each menu action
**Assert:** `open_clicked` signal fires for "Open File...", `open_folder_clicked` for "Open Folder...".

---

## Test Suite D: Integration with Probe Persistence

### D1. `test_sidecar_roundtrip_across_files`
**Setup:**
1. Load folder → select file A → add probes → switch to file B
2. Add different probes → switch back to file A
**Assert:** File A's probes restored. File B's probes restored on switch back.

### D2. `test_sidecar_not_created_if_no_probes`
**Setup:** Load folder → select file → don't add any probes → switch to another file
**Assert:** No `.pyprobe` sidecar created for the first file.

### D3. `test_watch_scalars_cleared_on_file_switch`
**Setup:** Load folder → select file → add scalar watch → switch file
**Assert:** Scalar watch sidebar is empty after switch.

---

## Implementation Notes

- **Suite A:** Add to `tests/test_e2e_folder_browsing.py` (unittest pattern, subprocess)
- **Suite B–D:** Add to `tests/gui/test_folder_browsing.py` (pytest + pytest-qt, in-process)
- **Regression scripts:** Create `regression/folder_test/` directory with fixture scripts
- **Temp folders:** Use `tempfile.mkdtemp()` + cleanup for stress tests (C2–C5)
- Tests in Suite B need a `main_window` fixture that creates + tears down `MainWindow` in-process (careful with `qapp` lifecycle)
- For B4/B5/B6: Simulate tree click by calling `_file_tree._on_clicked()` directly with the correct `QModelIndex`, or by calling `_on_file_tree_selected(path)` (signal-level testing)
- Suite C stress tests should run with `QTimer.singleShot(0, ...)` + `qapp.processEvents()` to simulate real event loop pressure

---

## Priority

| Priority | Tests | Why |
|----------|-------|-----|
| P0 | B1, B2, B4, B5, B11, C11 | Core happy path + cleanup correctness |
| P1 | A1, A4, B3, B6, B8, B10, D1 | Regression safety + persistence |
| P2 | C1, C2, C3, C4, C10, D2, D3 | Edge cases + stress |
| P3 | B7, C5, C6, C7, C8, C9 | Robustness under adversarial conditions |
