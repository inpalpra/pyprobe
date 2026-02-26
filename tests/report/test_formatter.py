import pytest
from pathlib import Path
from pyprobe.report.report_model import (
    BugReport, OpenFileEntry, RecordedStep,
)
from pyprobe.report.formatter import ReportFormatter


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def formatter():
    return ReportFormatter()


@pytest.fixture
def minimal_report():
    return BugReport(description="Plot button did nothing.")


@pytest.fixture
def full_report():
    return BugReport(
        description="Equation re-plot failed after closing graph.",
        steps=(
            RecordedStep(seq_num=1, description="Clicked Plot for eq0", timestamp=1.0),
            RecordedStep(seq_num=2, description="Closed graph widget eq0", timestamp=2.0),
            RecordedStep(seq_num=3, description="Clicked Plot for eq0 again", timestamp=3.0),
        ),
        open_files=(
            OpenFileEntry(
                path="/tmp/dsp_demo.py",
                is_probed=True, is_executed=True, has_unsaved=False,
            ),
        ),
        environment={
            "pyprobe_version": "0.1.27",
            "python_version": "3.12.0",
            "platform": "darwin",
            "qt_version": "6.6.0",
            "plugins": ["scalar", "waveform"],
            "git_commit_hash": "abc1234",
        },
        logs="2026-01-01 INFO  Starting\n2026-01-01 ERROR Plot failed\n",
    )


# ── Golden output tests ───────────────────────────────────────────────────────

def test_render_minimal_report(formatter, minimal_report):
    """A BugReport with only a description produces non-empty output containing the description."""
    output = formatter.render(minimal_report)
    assert isinstance(output, str)
    assert len(output) > 0
    assert "Plot button did nothing." in output


def test_render_full_report(formatter, full_report):
    """A BugReport with all sections populated produces output containing key data from each."""
    output = formatter.render(full_report)
    assert "Equation re-plot failed" in output       # description
    assert "Clicked Plot for eq0" in output           # step
    assert "dsp_demo.py" in output                    # open file path
    assert "0.1.27" in output                         # environment value
    assert "Plot failed" in output                    # log line


def test_render_report_with_logs(formatter):
    """When logs is set, the rendered output contains those log lines verbatim."""
    report = BugReport(
        description="Check logs.",
        logs="WARNING: unexpected None\nERROR: tracer stopped\n",
    )
    output = formatter.render(report)
    assert "WARNING: unexpected None" in output
    assert "ERROR: tracer stopped" in output


def test_render_report_with_file_contents(formatter):
    """When OpenFileEntry.contents is set, the contents appear in the rendered output."""
    report = BugReport(
        description="File content test.",
        open_files=(
            OpenFileEntry(
                path="/tmp/script.py", is_probed=False, is_executed=True,
                has_unsaved=False, contents="import numpy as np\nx = np.zeros(1024)\n",
            ),
        ),
    )
    output = formatter.render(report)
    assert "import numpy as np" in output
    assert "x = np.zeros(1024)" in output


# ── Behavioral / conditional tests ───────────────────────────────────────────

def test_optional_section_omitted_when_none(formatter):
    """Sections corresponding to None fields produce no content in the output."""
    report = BugReport(description="Minimal.")
    output = formatter.render(report)
    # No step descriptions
    assert "Clicked" not in output
    # No environment version number pattern
    assert "0.1." not in output


def test_file_contents_omitted_when_entry_has_no_contents(formatter):
    """When OpenFileEntry.contents is None, no file content block appears."""
    report = BugReport(
        description="No contents.",
        open_files=(
            OpenFileEntry(
                path="/tmp/a.py", is_probed=False, is_executed=True,
                has_unsaved=False, contents=None,
            ),
        ),
    )
    output = formatter.render(report)
    assert "a.py" in output       # path still present
    assert "import" not in output  # but no content


def test_truncation_adds_warning_for_large_contents():
    """File contents exceeding max_file_bytes are truncated with a warning in the output."""
    large_content = "x = 1\n" * 100_000
    report = BugReport(
        description="Large file.",
        open_files=(
            OpenFileEntry(
                path="/tmp/big.py", is_probed=False, is_executed=True,
                has_unsaved=False, contents=large_content,
            ),
        ),
    )
    small_formatter = ReportFormatter(max_file_bytes=1024)
    output = small_formatter.render(report)
    assert len(output) < len(large_content)
    assert any(word in output.lower() for word in ("truncated", "truncation", "omitted", "bytes"))


def test_output_is_deterministic(formatter, full_report):
    """render(report) called twice on the same BugReport produces identical strings."""
    assert formatter.render(full_report) == formatter.render(full_report)


def test_paths_in_output_are_sanitized(formatter):
    """Home-directory paths injected into any field appear as <USER_HOME> in output."""
    home = str(Path.home())
    report = BugReport(
        description=f"File at {home}/repos/pyprobe crashed.",
        open_files=(
            OpenFileEntry(
                path=f"{home}/repos/pyprobe/script.py",
                is_probed=True, is_executed=True, has_unsaved=False,
            ),
        ),
        logs=f"ERROR in {home}/repos/pyprobe/tracer.py\n",
    )
    output = formatter.render(report)
    assert home not in output
    assert "<USER_HOME>" in output


def test_does_not_crash_on_empty_report(formatter):
    """BugReport with all optional fields None renders without raising."""
    report = BugReport(description="")
    output = formatter.render(report)
    assert isinstance(output, str)


# ── JSON output tests (M8) ────────────────────────────────────────────────────

import json


def test_render_json_is_valid_json():
    """render_json(report) returns a string that parses as valid JSON."""
    formatter = ReportFormatter()
    report = BugReport(description="JSON test.")
    output = formatter.render_json(report)
    parsed = json.loads(output)  # raises if invalid
    assert isinstance(parsed, dict)


def test_render_json_contains_steps():
    """JSON output includes a 'steps' key with seq_num, description, timestamp per entry."""
    formatter = ReportFormatter()
    report = BugReport(
        description="Steps test.",
        steps=(
            RecordedStep(seq_num=1, description="Clicked Run", timestamp=1_000_000.0),
            RecordedStep(seq_num=2, description="Closed widget", timestamp=1_000_001.0),
        ),
    )
    parsed = json.loads(formatter.render_json(report))
    assert "steps" in parsed
    assert len(parsed["steps"]) == 2
    step = parsed["steps"][0]
    assert "seq_num" in step
    assert "description" in step
    assert "timestamp" in step
    assert step["seq_num"] == 1
    assert step["description"] == "Clicked Run"


def test_render_json_contains_environment():
    """JSON output includes an 'environment' dict when environment is set."""
    formatter = ReportFormatter()
    report = BugReport(
        description="Env test.",
        environment={"pyprobe_version": "0.1.27", "platform": "darwin"},
    )
    parsed = json.loads(formatter.render_json(report))
    assert "environment" in parsed
    assert parsed["environment"]["pyprobe_version"] == "0.1.27"


def test_render_json_is_deterministic():
    """render_json(report) called twice on the same BugReport produces identical strings."""
    formatter = ReportFormatter()
    report = BugReport(
        description="Determinism test.",
        environment={"a": "1", "b": "2"},
    )
    assert formatter.render_json(report) == formatter.render_json(report)


def test_render_json_paths_are_sanitized():
    """No home-directory path appears anywhere in the JSON output."""
    home = str(Path.home())
    formatter = ReportFormatter()
    report = BugReport(
        description=f"Path at {home}/repos/pyprobe.",
        logs=f"ERROR in {home}/tracer.py",
    )
    output = formatter.render_json(report)
    assert home not in output
    assert "<USER_HOME>" in output
