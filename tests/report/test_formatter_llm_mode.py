import pytest
from pyprobe.report.report_model import (
    BugReport, OpenFileEntry, RecordedStep,
)
from pyprobe.report.formatter import ReportFormatter


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def formatter():
    return ReportFormatter()


SAMPLE_CODE = """\
import numpy as np

def generate_signal(n):
    t = np.linspace(0, 1, n)
    signal = np.sin(2 * np.pi * 10 * t)
    noise = np.random.randn(n) * 0.1
    return signal + noise

def process(data):
    filtered = np.convolve(data, np.ones(5)/5, mode='same')
    return filtered

if __name__ == '__main__':
    sig = generate_signal(1024)
    out = process(sig)
    print(out[:10])
"""


def _make_report_with_location_steps(
    contents: str | None = SAMPLE_CODE,
    include_file: bool = True,
) -> BugReport:
    """Helper: report with steps that contain ' @ file:line:col' locations."""
    steps = (
        RecordedStep(
            seq_num=1,
            description="Added probe: signal @ /tmp/dsp.py:5:4",
            timestamp=1.0,
        ),
        RecordedStep(
            seq_num=2,
            description="Script finished",
            timestamp=2.0,
        ),
        RecordedStep(
            seq_num=3,
            description="Added probe: filtered @ /tmp/dsp.py:11:4",
            timestamp=3.0,
        ),
    )
    open_files = (
        OpenFileEntry(
            path="/tmp/dsp.py",
            is_probed=True,
            is_executed=True,
            has_unsaved=False,
            contents=contents if include_file else None,
        ),
    )
    return BugReport(
        description="Probe shows stale data.",
        steps=steps,
        open_files=open_files,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_llm_mode_adds_location_legend(formatter):
    """LLM mode output contains the location format legend after the steps section."""
    report = _make_report_with_location_steps()
    output = formatter.render(report, llm_mode=True, include_full_file=True)
    assert "Location format: <symbol> @ <file>:<line>:<column>" in output


def test_llm_mode_adds_line_numbers(formatter):
    """LLM mode with full file renders every line with '{n:>4} | ' prefix."""
    report = _make_report_with_location_steps()
    output = formatter.render(report, llm_mode=True, include_full_file=True)
    assert "   1 | import numpy as np" in output
    assert "   5 |     signal = np.sin(2 * np.pi * 10 * t)" in output


def test_llm_mode_extracts_only_relevant_windows_when_full_file_unchecked(formatter):
    """When include_full_file=False, only ±5 lines around referenced lines appear."""
    # Use a file long enough that some lines fall outside ±5 of any reference
    long_code = "\n".join(f"line_{i} = {i}" for i in range(1, 31))  # 30 lines
    steps = (
        RecordedStep(seq_num=1, description="Added probe: x @ /tmp/long.py:5:4", timestamp=1.0),
    )
    open_files = (
        OpenFileEntry(
            path="/tmp/long.py", is_probed=True, is_executed=True,
            has_unsaved=False, contents=long_code,
        ),
    )
    report = BugReport(description="Window test.", steps=steps, open_files=open_files)
    output = formatter.render(report, llm_mode=True, include_full_file=False)
    # Line 5 referenced → window [1,10] should appear
    assert "   5 |" in output
    assert "  10 |" in output
    # Line 20 is well outside ±5 of line 5 → should NOT appear
    assert "  20 |" not in output


def test_llm_mode_merges_overlapping_ranges(formatter):
    """Two references 6 lines apart (5 and 11) with context=5 produce merged windows."""
    report = _make_report_with_location_steps()
    output = formatter.render(report, llm_mode=True, include_full_file=False)
    # Lines 5 and 11 are 6 apart; with ±5 context, ranges [1,10] and [6,16] overlap
    # → single merged window, no '...' separator
    assert "  ..." not in output


def test_llm_mode_full_file_includes_all_lines_with_numbers(formatter):
    """When include_full_file=True, all lines of the file appear with line numbers."""
    report = _make_report_with_location_steps()
    output = formatter.render(report, llm_mode=True, include_full_file=True)
    lines = SAMPLE_CODE.splitlines()
    total = len(lines)
    # First and last lines should both be present
    assert f"   1 | {lines[0]}" in output
    assert f"{total:>4} | {lines[-1]}" in output


def test_default_mode_unchanged_when_llm_mode_false(formatter):
    """render(report, llm_mode=False) produces identical output to render(report)."""
    report = _make_report_with_location_steps()
    default_output = formatter.render(report)
    explicit_false = formatter.render(report, llm_mode=False)
    assert default_output == explicit_false


def test_execution_events_not_removed_in_llm_mode(formatter):
    """System events like 'Script finished' are preserved in LLM mode steps."""
    report = _make_report_with_location_steps()
    output = formatter.render(report, llm_mode=True, include_full_file=True)
    assert "Script finished" in output


def test_default_mode_snippets_shows_windows(formatter):
    """Default mode with include_full_file=False shows snippet windows with line numbers."""
    long_code = "\n".join(f"line_{i} = {i}" for i in range(1, 31))
    steps = (
        RecordedStep(seq_num=1, description="Added probe: x @ /tmp/snip.py:5:4", timestamp=1.0),
    )
    open_files = (
        OpenFileEntry(
            path="/tmp/snip.py", is_probed=True, is_executed=True,
            has_unsaved=False, contents=long_code,
        ),
    )
    report = BugReport(description="Snippet test.", steps=steps, open_files=open_files)
    output = formatter.render(report, llm_mode=False, include_full_file=False)
    # Snippets should have line numbers
    assert "   5 |" in output
    # But not the full file
    assert "  20 |" not in output
    # No LLM-specific legend
    assert "Location format:" not in output


def test_file_without_referenced_lines_falls_back_to_full_contents(formatter):
    """A file with no matching referenced lines falls back to showing full contents."""
    steps = (
        RecordedStep(
            seq_num=1,
            description="Added probe: x @ /tmp/other.py:10:4",
            timestamp=1.0,
        ),
    )
    open_files = (
        OpenFileEntry(
            path="/tmp/unrelated.py",
            is_probed=False,
            is_executed=True,
            has_unsaved=False,
            contents="# this file has no referenced lines\nx = 1\n",
        ),
    )
    report = BugReport(
        description="Testing fallback.",
        steps=steps,
        open_files=open_files,
    )
    output = formatter.render(report, llm_mode=True, include_full_file=False)
    # File is still listed
    assert "/tmp/unrelated.py" in output
    assert "[executed]" in output
    # Falls back to full numbered contents since no references match this file
    assert "   1 | # this file has no referenced lines" in output
    assert "   2 | x = 1" in output
