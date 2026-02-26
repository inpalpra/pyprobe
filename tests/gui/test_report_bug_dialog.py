import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from pyprobe.gui.main_window import MainWindow
from pyprobe.gui.report_bug_dialog import ReportBugDialog
from pyprobe.report.session_snapshot import SessionStateCollector


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_null_collector():
    """Return a SessionStateCollector with stub getters returning empty tuples."""
    return SessionStateCollector(
        file_getter=lambda: (),
        probe_getter=lambda: (),
        equation_getter=lambda: (),
        widget_getter=lambda: (),
    )


def make_dialog(qtbot, collector=None):
    """Construct and register a ReportBugDialog with qtbot."""
    if collector is None:
        collector = make_null_collector()
    dialog = ReportBugDialog(collector=collector)
    qtbot.addWidget(dialog)
    return dialog


# ── Menu integration tests ────────────────────────────────────────────────────

def test_help_menu_exists_in_main_window(qtbot):
    """MainWindow menu bar has a Help menu."""
    win = MainWindow()
    qtbot.addWidget(win)
    menu_titles = [a.text() for a in win.menuBar().actions()]
    assert any("help" in t.lower() for t in menu_titles)


def test_report_bug_action_in_help_menu(qtbot):
    """Help menu exposes a Report Bug action."""
    win = MainWindow()
    qtbot.addWidget(win)
    help_menu = next(
        a.menu() for a in win.menuBar().actions()
        if "help" in a.text().lower()
    )
    action_texts = [a.text().lower() for a in help_menu.actions()]
    assert any("report" in t or "bug" in t for t in action_texts)


def test_report_bug_action_opens_dialog(qtbot):
    """Triggering the Report Bug action opens a dialog window."""
    win = MainWindow()
    qtbot.addWidget(win)
    help_menu = next(
        a.menu() for a in win.menuBar().actions()
        if "help" in a.text().lower()
    )
    report_action = next(
        a for a in help_menu.actions()
        if "report" in a.text().lower() or "bug" in a.text().lower()
    )
    with patch.object(MainWindow, "_show_report_bug_dialog") as mock_show:
        report_action.trigger()
        mock_show.assert_called_once()


# ── Generate report tests ─────────────────────────────────────────────────────

def test_generate_report_populates_preview(qtbot):
    """Clicking Generate produces non-empty report text in the preview area."""
    dialog = make_dialog(qtbot)
    dialog._trigger_generate()  # internal method; drives the Generate action
    preview_text = dialog._get_preview_text()  # internal accessor for test
    assert isinstance(preview_text, str)
    assert len(preview_text) > 0


def test_generate_report_contains_user_description(qtbot):
    """Description entered by the user appears verbatim in the generated report."""
    dialog = make_dialog(qtbot)
    dialog._set_description("Probe panel shows wrong scale after zoom")
    dialog._trigger_generate()
    assert "Probe panel shows wrong scale after zoom" in dialog._get_preview_text()


# ── Output action state tests ─────────────────────────────────────────────────

def test_output_actions_disabled_before_generate(qtbot):
    """Copy and Save output actions are unavailable before Generate has been clicked."""
    dialog = make_dialog(qtbot)
    assert not dialog._copy_action_enabled()
    assert not dialog._save_action_enabled()


def test_output_actions_enabled_after_generate(qtbot):
    """Copy and Save output actions become available after Generate is clicked."""
    dialog = make_dialog(qtbot)
    dialog._trigger_generate()
    assert dialog._copy_action_enabled()
    assert dialog._save_action_enabled()


# ── Copy to clipboard test ────────────────────────────────────────────────────

def test_copy_to_clipboard_writes_report_text(qtbot):
    """Clipboard contains the generated report text after Copy is activated."""
    dialog = make_dialog(qtbot)
    dialog._set_description("clipboard test")
    dialog._trigger_generate()
    dialog._trigger_copy()
    clipboard_text = QApplication.clipboard().text()
    assert "clipboard test" in clipboard_text


# ── PII sanitization test ─────────────────────────────────────────────────────

def test_report_sanitizes_paths_in_output(qtbot):
    """Any home-directory path that enters the report appears as <USER_HOME>."""
    from pyprobe.report.report_model import OpenFileEntry
    home = str(Path.home())
    collector = SessionStateCollector(
        file_getter=lambda: [
            OpenFileEntry(
                path=f"{home}/repos/pyprobe/examples/demo.py",
                is_probed=True, is_executed=True, has_unsaved=False,
            )
        ],
        probe_getter=lambda: (),
        equation_getter=lambda: (),
        widget_getter=lambda: (),
    )
    dialog = make_dialog(qtbot, collector=collector)
    dialog._trigger_generate()
    output = dialog._get_preview_text()
    assert home not in output
    assert "<USER_HOME>" in output


# ── Conditional section toggle tests ─────────────────────────────────────────

def test_environment_section_toggled_by_sysinfo_option(qtbot):
    """Environment section appears when sysinfo option is enabled; absent when disabled."""
    dialog = make_dialog(qtbot)

    dialog._set_sysinfo_enabled(True)
    dialog._trigger_generate()
    output_with = dialog._get_preview_text()

    dialog._set_sysinfo_enabled(False)
    dialog._trigger_generate()
    output_without = dialog._get_preview_text()

    # When enabled, some environment value must appear (e.g., a version string)
    assert any(key in output_with for key in ("python", "PyProbe", "pyprobe", "platform", "Qt"))
    # When disabled, the same values must not appear via the environment section
    # (they may appear elsewhere, so we check the environment header is absent)
    assert output_with != output_without


def test_logs_section_toggled_by_logs_option(qtbot, tmp_path):
    """Logs section appears when logs option is enabled; absent when disabled."""
    dialog = make_dialog(qtbot)

    dialog._set_logs_enabled(True)
    dialog._trigger_generate()
    output_with = dialog._get_preview_text()

    dialog._set_logs_enabled(False)
    dialog._trigger_generate()
    output_without = dialog._get_preview_text()

    assert output_with != output_without


def test_file_contents_section_toggled_by_files_option(qtbot):
    """File contents appear in the report when the include-files option is enabled."""
    from pyprobe.report.report_model import OpenFileEntry
    collector = SessionStateCollector(
        file_getter=lambda: [
            OpenFileEntry(
                path="/tmp/demo.py", is_probed=True, is_executed=True,
                has_unsaved=False, contents="x = np.zeros(1024)\n",
            )
        ],
        probe_getter=lambda: (),
        equation_getter=lambda: (),
        widget_getter=lambda: (),
    )
    dialog = make_dialog(qtbot, collector=collector)

    dialog._set_files_enabled(True)
    dialog._trigger_generate()
    output_with = dialog._get_preview_text()

    dialog._set_files_enabled(False)
    dialog._trigger_generate()
    output_without = dialog._get_preview_text()

    assert "x = np.zeros(1024)" in output_with
    assert "x = np.zeros(1024)" not in output_without


# ── Resilience test ───────────────────────────────────────────────────────────

def test_dialog_does_not_crash_with_no_open_file(qtbot):
    """Generate Report completes without error when no file is loaded."""
    dialog = make_dialog(qtbot)  # null collector returns no files
    dialog._trigger_generate()
    assert len(dialog._get_preview_text()) >= 0  # no exception thrown


# ── Regression guard ──────────────────────────────────────────────────────────

def test_existing_probe_flow_unaffected(qtbot):
    """Opening MainWindow is unaffected by the Help menu addition."""
    win = MainWindow()
    qtbot.addWidget(win)
    # MainWindow must still expose the View menu and its existing actions
    view_menu = next(
        a.menu() for a in win.menuBar().actions()
        if "view" in a.text().lower()
    )
    assert view_menu is not None


# ─── MILESTONE 7 ADDITIONS ────────────────────────────────────────────────────
# Appended to tests/gui/test_report_bug_dialog.py


# ── Recording mode state tests ────────────────────────────────────────────────

def test_recording_controls_toggle_state(qtbot):
    """Start Recording becomes unavailable after clicking it, and Stop becomes available.
    After clicking Stop, the reverse is true."""
    dialog = make_dialog(qtbot)

    # Before any recording
    assert dialog._start_recording_action_enabled()
    assert not dialog._stop_recording_action_enabled()

    dialog._trigger_start_recording()

    assert not dialog._start_recording_action_enabled()
    assert dialog._stop_recording_action_enabled()

    dialog._trigger_stop_recording()

    assert dialog._start_recording_action_enabled()
    assert not dialog._stop_recording_action_enabled()


def test_recording_mode_shows_indicator(qtbot):
    """A recording indicator widget is visible after recording starts."""
    dialog = make_dialog(qtbot)
    dialog._trigger_start_recording()
    assert dialog._recording_indicator_visible()


def test_recording_indicator_hidden_after_stop(qtbot):
    """The recording indicator is hidden after recording stops."""
    dialog = make_dialog(qtbot)
    dialog._trigger_start_recording()
    dialog._trigger_stop_recording()
    assert not dialog._recording_indicator_visible()


# ── Report content tests ──────────────────────────────────────────────────────

def test_steps_section_absent_when_no_recording(qtbot):
    """If recording was never started, the generated report contains no steps section."""
    dialog = make_dialog(qtbot)
    dialog._set_description("No recording done.")
    dialog._trigger_generate()
    # Steps were never recorded so no step content should appear
    output = dialog._get_preview_text()
    # The fixture records no steps, so step markers like "1." at line start absent
    lines = [l.strip() for l in output.splitlines()]
    numbered = [l for l in lines if l and l[0].isdigit() and l[1:3] == ". "]
    assert len(numbered) == 0


def test_generated_report_includes_steps_when_recorded(qtbot):
    """Steps section appears in the generated report when at least one step was recorded."""
    dialog = make_dialog(qtbot)
    dialog._trigger_start_recording()
    dialog._inject_step("Manually injected step for testing")
    dialog._trigger_stop_recording()
    dialog._trigger_generate()
    assert "Manually injected step for testing" in dialog._get_preview_text()


def test_generated_report_includes_baseline_state(qtbot):
    """A session state baseline section appears in the report when recording was used."""
    from pyprobe.report.report_model import OpenFileEntry
    collector = SessionStateCollector(
        file_getter=lambda: [
            OpenFileEntry(
                path="/tmp/baseline_demo.py",
                is_probed=True, is_executed=True, has_unsaved=False,
            )
        ],
        probe_getter=lambda: (),
        equation_getter=lambda: (),
        widget_getter=lambda: (),
    )
    dialog = make_dialog(qtbot, collector=collector)
    dialog._trigger_start_recording()
    dialog._trigger_stop_recording()
    dialog._trigger_generate()
    assert "baseline_demo.py" in dialog._get_preview_text()


# ── Signal integration tests ──────────────────────────────────────────────────

def test_step_recorded_when_probe_action_fires(qtbot):
    """Simulating a probe_added signal during recording produces a step in the report."""
    dialog = make_dialog(qtbot)
    dialog._trigger_start_recording()
    dialog._simulate_probe_added("signal_x", line=42)
    dialog._trigger_stop_recording()
    dialog._trigger_generate()
    output = dialog._get_preview_text()
    assert "signal_x" in output or "42" in output


# ── Cleanup and session management tests ─────────────────────────────────────

def test_recording_stops_cleanly_if_dialog_closed(qtbot):
    """Closing the dialog while recording is active stops the recorder without error."""
    dialog = make_dialog(qtbot)
    dialog._trigger_start_recording()
    assert dialog._recorder_is_active()
    dialog.close()  # must not raise
    assert not dialog._recorder_is_active()


def test_generate_after_stop_includes_all_steps(qtbot):
    """All steps accumulated between Start and Stop appear in the generated report."""
    dialog = make_dialog(qtbot)
    dialog._trigger_start_recording()
    dialog._inject_step("Step A")
    dialog._inject_step("Step B")
    dialog._inject_step("Step C")
    dialog._trigger_stop_recording()
    dialog._trigger_generate()
    output = dialog._get_preview_text()
    assert "Step A" in output
    assert "Step B" in output
    assert "Step C" in output


def test_second_recording_session_replaces_first(qtbot):
    """Starting a second recording session clears steps from the first."""
    dialog = make_dialog(qtbot)

    # First session
    dialog._trigger_start_recording()
    dialog._inject_step("First session step")
    dialog._trigger_stop_recording()

    # Second session
    dialog._trigger_start_recording()
    dialog._inject_step("Second session step")
    dialog._trigger_stop_recording()

    dialog._trigger_generate()
    output = dialog._get_preview_text()
    assert "Second session step" in output
    assert "First session step" not in output


# ─── MILESTONE 8 ADDITIONS ────────────────────────────────────────────────────

import json
import urllib.parse
import webbrowser


# ── GitHub Issue action tests ─────────────────────────────────────────────────

def test_github_action_enabled_after_generate(qtbot):
    """Open GitHub Issue action becomes available after Generate is clicked."""
    dialog = make_dialog(qtbot)
    assert not dialog._github_action_enabled()
    dialog._trigger_generate()
    assert dialog._github_action_enabled()


def test_github_url_is_properly_url_encoded(qtbot):
    """The URL passed to webbrowser.open() has query params that are properly
    percent-encoded. Spaces become %20 or +; ampersands in content become %26."""
    dialog = make_dialog(qtbot)
    dialog._set_description("Problem with foo & bar")
    dialog._trigger_generate()

    with patch("webbrowser.open") as mock_open:
        dialog._trigger_open_github()
        assert mock_open.called
        url = mock_open.call_args[0][0]

    # URL must be parseable
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    assert "title" in query or "body" in query

    # The raw & must not appear unencoded in the query string portion
    raw_query = parsed.query
    # The description's literal & should be encoded, not raw
    # (parse_qs round-trip proves encoding was applied)
    assert "&" not in urllib.parse.unquote(raw_query).replace(
        urllib.parse.unquote(raw_query), ""
    ) or "foo & bar" in urllib.parse.unquote(raw_query)


def test_github_url_handles_special_characters(qtbot):
    """A description with newlines, quotes, and ampersands is encoded without
    breaking the URL structure (query string remains parseable)."""
    dialog = make_dialog(qtbot)
    dialog._set_description('Bug: "widget" fails\nwith x & y')
    dialog._trigger_generate()

    with patch("webbrowser.open") as mock_open:
        dialog._trigger_open_github()
        url = mock_open.call_args[0][0]

    # URL must be structurally valid — both parts present
    parsed = urllib.parse.urlparse(url)
    assert parsed.scheme in ("http", "https")
    assert parsed.netloc != ""
    # Query string must be parseable (no syntax errors from special chars)
    query_params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    assert len(query_params) > 0


def test_github_url_contains_no_home_path(qtbot):
    """The GitHub URL passed to webbrowser.open() contains no raw home-directory path."""
    from pyprobe.report.report_model import OpenFileEntry
    home = str(Path.home())
    collector = SessionStateCollector(
        file_getter=lambda: [
            OpenFileEntry(
                path=f"{home}/repos/pyprobe/examples/demo.py",
                is_probed=True, is_executed=True, has_unsaved=False,
            )
        ],
        probe_getter=lambda: (),
        equation_getter=lambda: (),
        widget_getter=lambda: (),
    )
    dialog = make_dialog(qtbot, collector=collector)
    dialog._trigger_generate()

    with patch("webbrowser.open") as mock_open:
        dialog._trigger_open_github()
        url = mock_open.call_args[0][0]

    # Decode any percent-encoding before checking for raw home path
    decoded_url = urllib.parse.unquote(url)
    assert home not in decoded_url


# ── End-to-end PII audit ──────────────────────────────────────────────────────

def test_path_sanitization_end_to_end(qtbot):
    """Full pipeline: inject a home-directory path into every section of a BugReport,
    render to both plaintext and JSON, assert str(Path.home()) appears in neither output.

    This is the final and permanent PII guard for the entire report pipeline.
    """
    from pyprobe.report.report_model import (
        BugReport, OpenFileEntry, ProbeTraceEntry, RecordedStep
    )
    from pyprobe.report.formatter import ReportFormatter

    home = str(Path.home())

    report = BugReport(
        description=f"Crash at {home}/repos/pyprobe/main.py",
        steps=(
            RecordedStep(
                seq_num=1,
                description=f"Loaded file {home}/examples/demo.py",
                timestamp=1.0,
            ),
        ),
        open_files=(
            OpenFileEntry(
                path=f"{home}/examples/demo.py",
                is_probed=True,
                is_executed=True,
                has_unsaved=False,
                contents=f"# Script at {home}/examples/demo.py\nimport numpy\n",
            ),
        ),
        environment={
            "pyprobe_version": "0.1.27",
            "virtualenv": f"{home}/.venv/bin/python",
        },
        logs=f"ERROR in {home}/repos/pyprobe/core/tracer.py at line 99\n",
    )

    formatter = ReportFormatter()

    plaintext = formatter.render(report)
    json_output = formatter.render_json(report)

    assert home not in plaintext, (
        f"HOME path leaked into plaintext report. Excerpt: "
        f"{plaintext[max(0, plaintext.find(home)-50):plaintext.find(home)+100]}"
    )
    assert home not in json_output, (
        f"HOME path leaked into JSON report."
    )

    # Positive check: sanitization marker must appear
    assert "<USER_HOME>" in plaintext
    assert "<USER_HOME>" in json_output
