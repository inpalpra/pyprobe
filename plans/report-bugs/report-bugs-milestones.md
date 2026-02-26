# Report Bug Feature — TDD Milestone Plan

## Guiding Principles

1. **Tests first, implementation second.** Every milestone begins by writing failing tests that specify exact behavior; only then is the implementation written to make them pass.
2. **Zero regression tolerance.** Every milestone must leave `python run_tests.py` fully green before it is considered complete.
3. **Isolation ladder.** Early milestones touch zero GUI code (pure logic); later milestones progressively integrate. This lets the core logic be validated without any Qt dependency.
4. **Permanent regression suite.** Each milestone's tests become permanent regression guards for all future milestones and all future development.
5. **Lock semantics, not cosmetics.** Tests protect behavioral contracts — what data is present, which sections are conditionally included, whether output is deterministic and PII-free — not exact header phrasing or layout spacing.
6. **Performance guards are real but realistic.** Timing assertions exist to catch catastrophic regressions, not to enforce microsecond precision. All timing tests are marked `@pytest.mark.performance` so they can be excluded in constrained CI environments.

---

## Milestone Ordering Change vs. Initial Draft

SessionSnapshot (originally M4) is promoted to **M3** because it is required by the MVP dialog and is conceptually simpler — it has no filesystem dependency. LogCapture (originally M3) becomes **M4** since it is self-contained and independent of everything except M1.

---

## New Files / Modules Overview

```
pyprobe/
  report/
    __init__.py
    sanitizer.py          # M1 – PathSanitizer
    environment.py        # M1 – EnvironmentCollector
    report_model.py       # M2 – BugReport dataclass + section models
    formatter.py          # M2 – ReportFormatter (plaintext + JSON)
    session_snapshot.py   # M3 – SessionStateCollector
    log_capture.py        # M4 – LogCapture (reads log files)
    step_recorder.py      # M6 – StepRecorder (event capture)

tests/
  report/
    __init__.py
    test_sanitizer.py          # M1 regression tests
    test_environment.py        # M1 regression tests
    test_report_model.py       # M2 regression tests
    test_formatter.py          # M2 + M8 regression tests
    test_session_snapshot.py   # M3 regression tests
    test_log_capture.py        # M4 regression tests
    test_step_recorder.py      # M6 regression tests

tests/gui/
    test_report_bug_dialog.py  # M5 + M7 + M8 GUI regression tests
```

The new `report` sub-suite is added to `run_tests.py` as `--suite report`.

---

## Milestone 1 — Core Utilities: PathSanitizer & EnvironmentCollector

### Goal
Implement two pure-logic utilities with no Qt or GUI dependency.
`PathSanitizer` replaces user home directories with `<USER_HOME>` in any string.
`EnvironmentCollector` gathers Python version, PyProbe version, OS, Qt version, plugin list, and optionally the git commit hash.

### Why First
All subsequent milestones emit paths and environment info. Sanitization correctness must be validated in isolation before any report output can be trusted.

---

### Tests to Write First (`tests/report/test_sanitizer.py`)

```python
# All tests must FAIL before implementation begins

def test_sanitize_unix_home_in_path():
    """Absolute Unix home path is replaced with <USER_HOME>."""

def test_sanitize_windows_home_in_path():
    """Windows-style home path is replaced correctly on all platforms."""

def test_sanitize_does_not_alter_non_home_paths():
    """Paths outside the home directory are left unchanged."""

def test_sanitize_multiple_occurrences_in_one_string():
    """All occurrences of the home path in a multi-line string are replaced."""

def test_sanitize_empty_string_returns_empty():
    """Empty input returns empty output."""

def test_sanitize_path_with_tilde_expansion():
    """Paths written with ~ are also sanitized."""

def test_sanitize_preserves_relative_paths():
    """Relative paths are not modified."""

def test_sanitize_in_traceback_string():
    """Home path embedded inside a mock traceback string is sanitized."""
```

```python
# tests/report/test_environment.py

def test_environment_contains_python_version():
    """Collected env has 'python_version' key with a non-empty string."""

def test_environment_contains_pyprobe_version():
    """Collected env has 'pyprobe_version' matching pyprobe.__version__."""

def test_environment_contains_platform():
    """Collected env has 'platform' key."""

def test_environment_contains_qt_version():
    """Collected env has 'qt_version' key with a non-empty string."""

def test_environment_contains_plugin_list():
    """Collected env has 'plugins' as a list (may be empty)."""

def test_environment_git_hash_is_string_or_unknown():
    """git_commit_hash is a non-empty string or the literal 'unknown'."""

def test_environment_paths_are_sanitized():
    """Any paths inside the env snapshot are sanitized via PathSanitizer."""

@pytest.mark.performance
def test_environment_collection_is_fast():
    """EnvironmentCollector.collect() completes in under 2 seconds.
    Marked performance: excluded in constrained CI via -m 'not performance'."""
```

### Implementation Scope (`pyprobe/report/sanitizer.py`, `environment.py`)

- `PathSanitizer.sanitize(text: str) -> str` — replaces all occurrences of `str(Path.home())` and `os.path.expanduser("~")` with `<USER_HOME>`.
- `EnvironmentCollector.collect() -> dict` — reads from `pyprobe.__version__`, `sys.version`, `platform.system()`, `PyQt6.QtCore.QT_VERSION_STR` (imported lazily to avoid forcing Qt in pure-logic tests), `PluginRegistry.instance()`, and a subprocess call to `git rev-parse --short HEAD` (with `"unknown"` fallback).

### Regression Tests Added (must pass forever)

All 16 tests above. Any future change to path handling or version reporting must not break them.

---

## Milestone 2 — Report Data Model & Plaintext Formatter

### Goal
Define the complete `BugReport` data model as frozen dataclasses with immutable nested collections.
Implement `ReportFormatter` which renders any `BugReport` to the canonical plaintext format.

No GUI, no file I/O, no subprocess calls.

---

### Tests to Write First (`tests/report/test_report_model.py`)

```python
def test_bug_report_is_constructable_with_minimum_fields():
    """BugReport(description='X') works; all optional sections default to None."""

def test_open_file_entry_has_required_fields():
    """OpenFileEntry has: path, is_probed, is_executed, has_unsaved, contents (optional)."""

def test_probe_trace_entry_has_required_fields():
    """ProbeTraceEntry has: name, source_file, shape, dtype."""

def test_equation_entry_has_required_fields():
    """EquationEntry has: eq_id, expression, status, is_plotted."""

def test_graph_widget_entry_has_required_fields():
    """GraphWidgetEntry has: widget_id, what_plotted, is_docked, is_visible."""

def test_recorded_step_has_required_fields():
    """RecordedStep has: seq_num (int), description (str), timestamp (float)."""

def test_bug_report_top_level_is_immutable():
    """Assigning to a BugReport field raises FrozenInstanceError."""

def test_bug_report_internal_lists_are_immutable():
    """Nested collection fields (open_files, probed_traces, etc.) are tuples,
    not mutable lists. Attempting to append to them raises AttributeError or TypeError."""
```

### Tests to Write First (`tests/report/test_formatter.py`)

The formatter test strategy uses **golden-output tests** to guard the overall shape of the report, plus **targeted behavioral tests** to guard the conditional logic. Individual header wording and layout spacing are not locked — the golden tests will catch any semantic loss.

```python
# --- Golden output tests ---

def test_render_minimal_report():
    """A BugReport with only a description produces output that contains the description.
    The output is non-empty and contains at least one recognizable section marker."""

def test_render_full_report():
    """A BugReport with all optional sections populated produces output that
    contains: description, each open file's path, at least one step, env key values,
    and log lines. Uses snapshot assertion or substring checks — not exact layout."""

def test_render_report_with_logs():
    """When logs is set, the rendered output contains the log lines verbatim."""

def test_render_report_with_file_contents():
    """When OpenFileEntry.contents is set, the rendered output contains those
    file contents inside a delimited block."""

# --- Behavioral / conditional tests ---

def test_optional_section_omitted_when_none():
    """Sections that correspond to None fields in BugReport do not appear
    in the output (no orphaned headers)."""

def test_file_contents_omitted_when_none():
    """When OpenFileEntry.contents is None, no contents block appears for that file."""

def test_truncation_adds_warning_for_large_contents():
    """File contents exceeding max_file_bytes are truncated and the output
    contains a truncation warning indicating the original size."""

def test_output_is_deterministic():
    """Calling render(report) twice on the same BugReport produces identical strings."""

def test_paths_in_output_are_sanitized():
    """Any home-directory path injected into any field of BugReport is replaced
    with <USER_HOME> in the rendered output."""

def test_does_not_crash_on_empty_report():
    """BugReport with all optional fields None renders without raising an exception."""
```

### Implementation Scope

- `pyprobe/report/report_model.py` — frozen dataclasses: `BugReport`, `OpenFileEntry`, `ProbeTraceEntry`, `EquationEntry`, `GraphWidgetEntry`, `RecordedStep`, `SessionState`. All nested collection fields stored as `tuple`, not `list`, to enforce immutability inside a frozen dataclass.
- `pyprobe/report/formatter.py` — `ReportFormatter` with `render(report: BugReport) -> str`; applies `PathSanitizer` automatically; `max_file_bytes` constructor argument (default 50 KB) controls truncation. `render_json` method added in M8.

### Regression Tests Added

All 18 tests above. The golden tests protect semantic completeness; behavioral tests protect conditional logic. Cosmetic reformatting is permitted as long as all tests pass.

---

## Milestone 3 — SessionStateCollector

### Goal
Implement `SessionStateCollector`, which builds a `SessionState` snapshot by calling injected getter callables. The collector is fully testable without any Qt application because all GUI dependencies are provided as constructor arguments.

Promoted before LogCapture because it is needed by the M5 dialog MVP.

---

### Tests to Write First (`tests/report/test_session_snapshot.py`)

```python
def make_minimal_collector(**overrides):
    """Helper: returns a SessionStateCollector with stub getters returning empty tuples.
    Overrides allow injecting specific getters per test."""

def test_snapshot_contains_open_files_from_getter():
    """Snapshot.open_files matches what the file_getter returns."""

def test_snapshot_contains_probed_traces_from_getter():
    """Snapshot.probed_traces matches what the probe_getter returns."""

def test_snapshot_contains_equations_from_getter():
    """Snapshot.equations matches what the equation_getter returns."""

def test_snapshot_contains_graph_widgets_from_getter():
    """Snapshot.graph_widgets matches what the widget_getter returns."""

def test_snapshot_records_capture_timestamp():
    """Snapshot.captured_at is a float close to time.time() at collection time."""

def test_snapshot_is_immutable_after_capture():
    """Modifying the source list after capture does not alter the snapshot's fields."""

def test_baseline_state_is_snapshot_not_live_reference():
    """The snapshot holds a frozen copy of the data at collection time.
    If the original mutable structure is later mutated, the snapshot is unchanged."""

def test_snapshot_does_not_raise_when_getter_returns_none():
    """If any getter returns None, the corresponding section is an empty tuple."""

def test_snapshot_does_not_raise_when_getter_raises():
    """If any getter raises an exception, the section is an empty tuple (no propagation)."""

def test_snapshot_paths_in_open_files_are_sanitized():
    """File paths in the snapshot have HOME replaced with <USER_HOME>."""

def test_snapshot_paths_in_probe_sources_are_sanitized():
    """Probe source_file paths in the snapshot have HOME sanitized."""

@pytest.mark.performance
def test_collect_is_fast_under_load():
    """Collector returns within 500ms when getters return 1000 items each.
    Marked performance: excluded in constrained CI via -m 'not performance'."""
```

### Implementation Scope

- `pyprobe/report/session_snapshot.py` — `SessionStateCollector` accepts: `file_getter`, `probe_getter`, `equation_getter`, `widget_getter` (all `Callable[[], Iterable]`).
- `collect() -> SessionState` — calls each getter inside `try/except`, converts results to `tuple`, freezes into `SessionState`.

### Integration Note (wired in M5)

`MainWindow` passes lambdas reading from `self._code_viewer`, `self._probe_controller`, `self._equation_manager`, and the panel container. Unit tests here use stubs only.

### Regression Tests Added

All 12 tests above. Guarantees: snapshot never raises; always returns a frozen copy; always sanitizes; live-reference isolation is enforced.

---

## Milestone 4 — Log Capture Module

### Goal
Implement `LogCapture`, which reads from PyProbe's log files, extracts the last N lines, separates tracebacks from regular log lines, and returns structured data for insertion into a `BugReport`.

---

### Tests to Write First (`tests/report/test_log_capture.py`)

```python
@pytest.fixture
def temp_log(tmp_path):
    """Creates a temp log file populated with synthetic log lines."""

def test_log_capture_returns_last_n_lines(temp_log):
    """capture(log_path, n=5) returns at most 5 lines."""

def test_log_capture_returns_all_when_fewer_than_n(temp_log):
    """Returns all lines if file has fewer than n lines."""

def test_log_capture_empty_file_returns_snapshot_with_empty_content(temp_log):
    """Empty log file returns a LogSnapshot with empty raw_lines, not None."""

def test_log_capture_missing_file_returns_none():
    """Non-existent log path returns None without raising."""

def test_log_capture_sanitizes_paths_in_log_lines(temp_log):
    """Home paths embedded in log lines are replaced with <USER_HOME>."""

def test_log_capture_extracts_tracebacks(temp_log):
    """Lines beginning a traceback block appear in LogSnapshot.tracebacks."""

def test_log_capture_extracts_warnings_and_errors(temp_log):
    """Lines with WARNING or ERROR level appear in LogSnapshot.warnings_and_errors."""

def test_log_capture_does_not_raise_on_permission_error(tmp_path):
    """Unreadable file returns None gracefully (PermissionError not propagated)."""
```

### Implementation Scope

- `pyprobe/report/log_capture.py` — `LogCapture.capture(log_path: str | None = None, n: int = 200) -> LogSnapshot | None`. `LogSnapshot`: `raw_lines: str`, `tracebacks: list[str]`, `warnings_and_errors: list[str]`. Default log path: `/tmp/pyprobe_debug.log`.

### Regression Tests Added

All 9 tests. Guaranteed: log capture never propagates exceptions; always sanitizes; respects line limits.

---

## Milestone 5 — ReportBugDialog + Help Menu (MVP, No Recording)

### Goal
Integrate M1–M4 into a working end-to-end bug report flow:

1. Add a **Help** menu to `MainWindow` with a **Report Bug** action.
2. Create `ReportBugDialog` with the complete UI from the spec, minus recording controls (those come in M7).
3. Wire "Generate Report" to build and render a `BugReport` from live session state.
4. Provide **Copy to Clipboard** and **Save to File** output actions.

---

### Tests to Write First (`tests/gui/test_report_bug_dialog.py`)

GUI tests use `pytest-qt` (`qtbot`, `qapp`). Tests protect behavioral flow and conditional output — not widget tree structure or exact label strings.

```python
def test_help_menu_exists_in_main_window(qtbot):
    """MainWindow menu bar has a Help menu."""

def test_report_bug_action_in_help_menu(qtbot):
    """Help menu exposes a Report Bug action."""

def test_report_bug_action_opens_dialog(qtbot):
    """Triggering Report Bug opens a dialog window."""

def test_generate_report_populates_preview(qtbot):
    """Clicking Generate produces non-empty report text in the preview area."""

def test_generate_report_contains_user_description(qtbot):
    """Description entered by the user appears verbatim in the generated report."""

def test_output_actions_disabled_before_generate(qtbot):
    """Copy and Save actions are unavailable before Generate has been clicked."""

def test_output_actions_enabled_after_generate(qtbot):
    """Copy and Save actions become available after Generate is clicked."""

def test_copy_to_clipboard_writes_report_text(qtbot):
    """Clipboard contains the generated report text after Copy is activated."""

def test_report_sanitizes_paths_in_output(qtbot):
    """Any home-directory path in the generated report is replaced with <USER_HOME>."""

def test_environment_section_toggled_by_sysinfo_option(qtbot):
    """Environment section appears in report when the sysinfo option is enabled,
    and is absent when the option is disabled."""

def test_logs_section_toggled_by_logs_option(qtbot):
    """Logs section appears when the logs option is enabled, absent when disabled."""

def test_file_contents_section_toggled_by_files_option(qtbot):
    """File contents appear in the report when the include-files option is enabled."""

def test_dialog_does_not_crash_with_no_open_file(qtbot):
    """Generate Report completes without error when no file is loaded in the viewer."""

def test_existing_probe_flow_unaffected(qtbot):
    """Opening MainWindow and exercising the probe flow is unaffected by the Help menu addition."""
```

### Implementation Scope

- `pyprobe/gui/report_bug_dialog.py` — `ReportBugDialog(QDialog)`.
- Edit `pyprobe/gui/main_window.py`: add `_setup_help_menu()`, call it after `_setup_theme_menu()`, add `_show_report_bug_dialog()` that creates the dialog and injects `SessionStateCollector` getters from live GUI objects.

### Regression Tests Added

All 14 tests above. The dialog behavioral contract is locked. Future milestones modifying the dialog must not break these.

---

## Milestone 6 — StepRecorder (Event Capture Engine)

### Goal
Implement `StepRecorder` — subscribes to existing Qt signals and accumulates `RecordedStep` objects. Recording must have zero measurable overhead when inactive.

---

### Tests to Write First (`tests/report/test_step_recorder.py`)

Tests use minimal Qt objects or mocks with `qtbot`. No full MainWindow needed.

```python
def test_recorder_starts_inactive():
    """StepRecorder.is_recording is False immediately after construction."""

def test_start_sets_is_recording_true():
    """After recorder.start(), is_recording is True."""

def test_stop_sets_is_recording_false():
    """After recorder.start(); recorder.stop(), is_recording is False."""

def test_record_step_appends_when_active():
    """recorder.record('did X') appends a RecordedStep while recording."""

def test_record_step_increments_seq_num():
    """Consecutive record() calls produce seq_num values 1, 2, 3, …"""

def test_record_step_has_timestamp():
    """RecordedStep.timestamp is close to time.time() at call time."""

def test_record_ignored_when_inactive():
    """record() calls before start() or after stop() do not appear in steps."""

def test_clear_resets_steps_and_seq_num():
    """recorder.clear() empties steps and resets seq_num to 0."""

def test_connect_signal_records_step_when_active(qtbot):
    """recorder.connect_signal(signal, 'did X') causes 'did X' in steps when signal fires during recording."""

def test_connect_signal_ignored_when_inactive(qtbot):
    """Signal firing before start() does not produce any steps."""

def test_connect_signal_with_formatter_callable(qtbot):
    """recorder.connect_signal(signal, fn) uses fn(*args) as the step description."""

def test_stop_disconnects_signals(qtbot):
    """After recorder.stop(), signals that were connected no longer produce steps,
    even if the signals continue to fire."""

def test_start_twice_does_not_duplicate_connections(qtbot):
    """Calling recorder.start() twice does not cause a single signal emission
    to record two steps (no double-connection)."""

def test_steps_frozen_at_stop():
    """The steps collection returned after stop() does not grow if record() is called again."""

def test_recorder_instances_are_independent():
    """Two StepRecorder instances share no state."""

@pytest.mark.performance
def test_overhead_when_inactive_is_negligible():
    """Calling record() 10,000 times on an inactive recorder completes in under 20 ms.
    Marked performance: excluded in constrained CI via -m 'not performance'."""
```

### Implementation Scope

- `pyprobe/report/step_recorder.py` — `StepRecorder`:
  - `start()` / `stop()` / `clear()`
  - `record(description: str)` — appends `RecordedStep` only when active
  - `connect_signal(signal, description: str | Callable[..., str])` — stores `(signal, slot)` pairs for clean disconnect on `stop()`
  - `steps: tuple[RecordedStep, ...]` — frozen on `stop()`; mutable internally during recording
  - `is_recording: bool` property

### Regression Tests Added

All 16 tests above. Signal lifecycle correctness (`test_stop_disconnects_signals`, `test_start_twice_does_not_duplicate_connections`) is permanently guarded. The performance bound is realistic and marked to prevent CI flakiness.

---

## Milestone 7 — Recording Mode Integration in Dialog

### Goal
Wire `StepRecorder` into `ReportBugDialog` and `MainWindow`:

1. Expose **Start Recording** / **Stop Recording** controls in the dialog.
2. On start: capture a `SessionState` baseline snapshot, show a floating **● Recording Steps** indicator, hook signals.
3. On stop: disconnect signal hooks, freeze steps.
4. On **Generate Report**: embed baseline snapshot + steps into the `BugReport`.

---

### Tests to Write First (added to `tests/gui/test_report_bug_dialog.py`)

```python
def test_recording_controls_toggle_state(qtbot):
    """Start Recording becomes unavailable and Stop becomes available after starting;
    reversed after stopping. Both transitions tested in one behavioral test."""

def test_recording_mode_shows_indicator(qtbot):
    """A visible recording indicator widget appears after recording starts."""

def test_recording_indicator_hidden_after_stop(qtbot):
    """The recording indicator is hidden after recording stops."""

def test_generated_report_includes_steps_when_recorded(qtbot):
    """Steps section appears in the generated report when at least one step was recorded."""

def test_generated_report_includes_baseline_state(qtbot):
    """A baseline session state section appears in the report when recording was used."""

def test_steps_section_absent_when_no_recording(qtbot):
    """Steps section is absent from the report if recording was never started."""

def test_step_recorded_when_probe_action_fires(qtbot):
    """Simulating a probe_added signal during recording produces a corresponding step in the report."""

def test_recording_stops_cleanly_if_dialog_closed(qtbot):
    """Closing the dialog while recording is active stops the recorder without error or signal leak."""

def test_generate_after_stop_includes_all_steps(qtbot):
    """All steps accumulated between Start and Stop appear in the generated report."""

def test_second_recording_session_replaces_first(qtbot):
    """Starting, stopping, then starting again clears previous steps before the new session."""
```

### Signals to Hook

| Source | Signal | Step Description |
|---|---|---|
| `ProbeController` | `probe_added(anchor, panel)` | `"Added probe: {anchor.symbol} at line {anchor.line}"` |
| `ProbeController` | `probe_removed(anchor)` | `"Removed probe: {anchor.symbol} at line {anchor.line}"` |
| `ControlBar` | run clicked | `"Clicked Run"` |
| `ControlBar` | stop clicked | `"Clicked Stop"` |
| Menu actions | `triggered` | `"Menu: {action_text}"` |
| `EquationManager` | equation added | `"Added equation: {eq_id}"` |
| `EquationManager` | equation changed | `"Edited equation: {eq_id} = {expr}"` |
| `CodeViewer` | file loaded | `"Loaded file: {sanitized_path}"` |

### Floating Recording Indicator

- `pyprobe/gui/recording_indicator.py` — `RecordingIndicator(QWidget)`: always-on-top, frameless, red dot + label. Shown by dialog on start, hidden on stop.

### Regression Tests Added

All 10 tests above. Recording flow behavioral contract is locked.

---

## Milestone 8 — Extended Output Options & Polish

### Goal
1. **Open GitHub Issue** — opens browser with pre-filled, URL-encoded title and body.
2. **Deterministic JSON event log** — `render_json(report)` serializes all sections.
3. **End-to-end PII audit** — full pipeline test confirming no home path leaks anywhere.

---

### Tests to Write First

```python
# tests/report/test_formatter.py (additions)

def test_render_json_is_valid_json():
    """ReportFormatter.render_json(report) returns parseable JSON."""

def test_render_json_contains_steps():
    """JSON output includes 'steps' with seq_num, description, timestamp per entry."""

def test_render_json_contains_environment():
    """JSON output includes 'environment' dict."""

def test_render_json_is_deterministic():
    """render_json(report) called twice produces identical strings."""

def test_render_json_paths_are_sanitized():
    """No home-directory path appears in JSON output."""

# tests/gui/test_report_bug_dialog.py (additions)

def test_github_action_enabled_after_generate(qtbot):
    """Open GitHub Issue action becomes available after Generate is clicked."""

def test_github_url_is_properly_url_encoded(qtbot, monkeypatch):
    """The URL passed to webbrowser.open() has title and body query params
    that are properly percent-encoded (spaces → %20 or +, & → %26, etc.)."""

def test_github_url_handles_special_characters(qtbot, monkeypatch):
    """A description containing newlines, quotes, and ampersands is correctly
    encoded in the GitHub URL without breaking URL structure."""

def test_github_url_contains_no_home_path(qtbot, monkeypatch):
    """The GitHub URL passed to webbrowser.open() contains no raw home-directory path."""

def test_path_sanitization_end_to_end(qtbot):
    """Full pipeline: inject a home-directory path into every section of a BugReport,
    render to plaintext and JSON, assert str(Path.home()) appears in neither output."""
```

### Implementation Scope

- `ReportFormatter.render_json(report: BugReport) -> str` — JSON-serializes all sections; applies `PathSanitizer`.
- `ReportBugDialog._on_open_github()` — builds URL using `urllib.parse.urlencode`; calls `webbrowser.open()`.
- GitHub repo URL stored as a constant in `pyprobe/__init__.py`.

### Regression Tests Added

All 10 tests above. The URL encoding tests and end-to-end PII test are permanent.

---

## Regression Test Summary Table

| Suite | Tests | What Is Guaranteed |
|---|---|---|
| `tests/report/test_sanitizer.py` | 8 | Path sanitization correctness |
| `tests/report/test_environment.py` | 8 | Env collection valid, sanitized, fast* |
| `tests/report/test_report_model.py` | 8 | Data model immutable; nested collections are tuples |
| `tests/report/test_formatter.py` | 10 + 5 | Report semantics locked; JSON format locked; no PII |
| `tests/report/test_session_snapshot.py` | 12 | Snapshot never raises; live-ref isolation; sanitized |
| `tests/report/test_log_capture.py` | 9 | Log capture never raises; sanitized; respects limits |
| `tests/report/test_step_recorder.py` | 16 | Signal lifecycle correct; no duplicates; fast* |
| `tests/gui/test_report_bug_dialog.py` | 14 + 10 + 4 | Dialog flow; recording flow; GitHub URL encoding |
| **Total new tests** | **~96** | All permanent |

_\* Performance-marked tests excluded under `-m 'not performance'`._

---

## Milestone Completion Checklist

Each milestone is done when:
- [ ] All new tests written and confirmed **failing** before implementation begins
- [ ] All new tests pass (green) after implementation
- [ ] `python run_tests.py` is **fully green** (all existing + all new tests)
- [ ] No new `# noqa` / `# type: ignore` without justification
- [ ] Code follows existing patterns: `get_logger(__name__)`, frozen dataclasses, `instance()` singletons where appropriate

---

## Dependency Graph

```
M1 (PathSanitizer + EnvironmentCollector)
  └── M2 (BugReport model + ReportFormatter)
        ├── M3 (SessionStateCollector)      ← promoted; needed by M5
        │     └── M5 (Dialog MVP)
        └── M4 (LogCapture)                 ← independent; feeds M5
              └── M5 (Dialog MVP)
                    └── M6 (StepRecorder)
                          └── M7 (Recording Mode)
                                └── M8 (Extended Output + PII audit)
```

M3 and M4 are independent of each other and may be developed in parallel after M2.

---

## Non-Functional Regression Guards

| Requirement | Test | Assertion |
|---|---|---|
| No overhead when not recording | `test_step_recorder.py::test_overhead_when_inactive_is_negligible` | 10,000 calls < 20 ms `@performance` |
| Env collection completes | `test_environment.py::test_environment_collection_is_fast` | < 2 s `@performance` |
| Snapshot collection fast | `test_session_snapshot.py::test_collect_is_fast_under_load` | < 500 ms @ 1000 items `@performance` |
| No PII in plaintext or JSON | `test_formatter.py::test_path_sanitization_end_to_end` | `str(Path.home())` absent |
| No crash on corrupt getter | `test_session_snapshot.py::test_snapshot_does_not_raise_when_getter_raises` | Empty section, no exception |
| No crash on missing log | `test_log_capture.py::test_log_capture_missing_file_returns_none` | Returns `None`, no exception |
| Signal disconnect on stop | `test_step_recorder.py::test_stop_disconnects_signals` | Steps not appended post-stop |
| No duplicate signal connections | `test_step_recorder.py::test_start_twice_does_not_duplicate_connections` | One step per signal emit |
| Snapshot is a frozen copy | `test_session_snapshot.py::test_baseline_state_is_snapshot_not_live_reference` | Mutation after capture has no effect |
| Nested model fields are tuples | `test_report_model.py::test_bug_report_internal_lists_are_immutable` | `TypeError` on append |
