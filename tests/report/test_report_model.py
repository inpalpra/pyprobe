import pytest
from dataclasses import FrozenInstanceError
from pyprobe.report.report_model import (
    BugReport, OpenFileEntry, ProbeTraceEntry,
    EquationEntry, GraphWidgetEntry, RecordedStep, SessionState,
)


def test_bug_report_is_constructable_with_minimum_fields():
    """BugReport(description='X') works; all optional sections default to None."""
    report = BugReport(description="Something went wrong")
    assert report.description == "Something went wrong"
    assert report.steps is None
    assert report.baseline_state is None
    assert report.open_files is None
    assert report.environment is None
    assert report.logs is None


def test_open_file_entry_has_required_fields():
    """OpenFileEntry exposes path, is_probed, is_executed, has_unsaved, contents."""
    entry = OpenFileEntry(
        path="/tmp/script.py", is_probed=True, is_executed=True, has_unsaved=False
    )
    assert entry.path == "/tmp/script.py"
    assert entry.is_probed is True
    assert entry.contents is None  # default
    with_contents = OpenFileEntry(
        path="/tmp/script.py", is_probed=True, is_executed=True,
        has_unsaved=False, contents="x = 1\n",
    )
    assert with_contents.contents == "x = 1\n"


def test_probe_trace_entry_has_required_fields():
    """ProbeTraceEntry exposes name, source_file, shape, dtype."""
    entry = ProbeTraceEntry(
        name="signal_x", source_file="/tmp/script.py",
        shape=(1024,), dtype="float32",
    )
    assert entry.name == "signal_x"
    assert entry.shape == (1024,)


def test_equation_entry_has_required_fields():
    """EquationEntry exposes eq_id, expression, status, is_plotted."""
    entry = EquationEntry(
        eq_id="eq0", expression="np.power(tr0, 2)", status="ok", is_plotted=True
    )
    assert entry.eq_id == "eq0"
    assert entry.is_plotted is True


def test_graph_widget_entry_has_required_fields():
    """GraphWidgetEntry exposes widget_id, what_plotted, is_docked, is_visible."""
    entry = GraphWidgetEntry(
        widget_id="w0", what_plotted="eq0", is_docked=True, is_visible=True
    )
    assert entry.widget_id == "w0"


def test_recorded_step_has_required_fields():
    """RecordedStep exposes seq_num (int), description (str), timestamp (float)."""
    step = RecordedStep(seq_num=1, description="Clicked Run", timestamp=1_234_567_890.0)
    assert step.seq_num == 1
    assert isinstance(step.timestamp, float)


def test_bug_report_top_level_is_immutable():
    """Assigning to a BugReport field after construction raises FrozenInstanceError."""
    report = BugReport(description="test")
    with pytest.raises(FrozenInstanceError):
        report.description = "changed"  # type: ignore[misc]


def test_bug_report_internal_lists_are_immutable():
    """Nested collection fields are tuples; append() raises AttributeError or TypeError."""
    report = BugReport(
        description="test",
        open_files=(
            OpenFileEntry(
                path="/tmp/a.py", is_probed=False, is_executed=True, has_unsaved=False
            ),
        ),
    )
    with pytest.raises((AttributeError, TypeError)):
        report.open_files.append(  # type: ignore[attr-defined]
            OpenFileEntry(
                path="/tmp/b.py", is_probed=False, is_executed=False, has_unsaved=False
            )
        )
