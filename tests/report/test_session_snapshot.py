import time
import pytest
from pyprobe.report.report_model import (
    OpenFileEntry, ProbeTraceEntry, EquationEntry, GraphWidgetEntry
)
from pyprobe.report.session_snapshot import SessionStateCollector


# ── Helper ────────────────────────────────────────────────────────────────────

def make_collector(**overrides):
    """Return a SessionStateCollector with stub getters returning empty tuples.
    Pass keyword overrides to replace specific getters for individual tests.
    """
    defaults = dict(
        file_getter=lambda: (),
        probe_getter=lambda: (),
        equation_getter=lambda: (),
        widget_getter=lambda: (),
    )
    defaults.update(overrides)
    return SessionStateCollector(**defaults)


# ── Section content tests ─────────────────────────────────────────────────────

def test_snapshot_contains_open_files_from_getter():
    """Snapshot.open_files matches what file_getter returns."""
    entry = OpenFileEntry(
        path="/tmp/a.py", is_probed=True, is_executed=True, has_unsaved=False
    )
    collector = make_collector(file_getter=lambda: [entry])
    snapshot = collector.collect()
    assert len(snapshot.open_files) == 1
    assert snapshot.open_files[0].is_probed is True


def test_snapshot_contains_probed_traces_from_getter():
    """Snapshot.probed_traces matches what probe_getter returns."""
    entry = ProbeTraceEntry(
        symbol="sig", file="/tmp/a.py", line=1, column=1, shape=(512,), dtype="float32"
    )
    collector = make_collector(probe_getter=lambda: [entry])
    snapshot = collector.collect()
    assert len(snapshot.probed_traces) == 1
    assert snapshot.probed_traces[0].symbol == "sig"


def test_snapshot_contains_equations_from_getter():
    """Snapshot.equations matches what equation_getter returns."""
    entry = EquationEntry(
        eq_id="eq0", expression="np.power(tr0, 2)", status="ok", is_plotted=True
    )
    collector = make_collector(equation_getter=lambda: [entry])
    snapshot = collector.collect()
    assert len(snapshot.equations) == 1
    assert snapshot.equations[0].eq_id == "eq0"


def test_snapshot_contains_graph_widgets_from_getter():
    """Snapshot.graph_widgets matches what widget_getter returns."""
    from pyprobe.report.report_model import WidgetTraceEntry
    entry = GraphWidgetEntry(
        widget_id="w0", is_docked=True, is_visible=True, lens="Waveform",
        primary_trace=WidgetTraceEntry(trace_id="tr0", components=("tr0.val",)),
        overlay_traces=()
    )
    collector = make_collector(widget_getter=lambda: [entry])
    snapshot = collector.collect()
    assert len(snapshot.graph_widgets) == 1
    assert snapshot.graph_widgets[0].widget_id == "w0"


# ── Timestamp test ────────────────────────────────────────────────────────────

def test_snapshot_records_capture_timestamp():
    """Snapshot.captured_at is close to time.time() at collection time."""
    before = time.time()
    snapshot = make_collector().collect()
    after = time.time()
    assert before <= snapshot.captured_at <= after


# ── Immutability tests ────────────────────────────────────────────────────────

def test_snapshot_is_immutable_after_capture():
    """Modifying the source list after collect() does not alter the snapshot."""
    source = [
        OpenFileEntry(
            path="/tmp/a.py", is_probed=False, is_executed=True, has_unsaved=False
        )
    ]
    collector = make_collector(file_getter=lambda: source)
    snapshot = collector.collect()
    source.append(
        OpenFileEntry(
            path="/tmp/b.py", is_probed=False, is_executed=False, has_unsaved=False
        )
    )
    assert len(snapshot.open_files) == 1  # snapshot unchanged


def test_baseline_state_is_snapshot_not_live_reference():
    """The snapshot holds a frozen copy. Mutating the original structure after
    collect() has no effect on any field of the snapshot."""
    inner = {"symbol": "sig", "file": "/tmp/a.py", "line": 1, "column": 1, "shape": (128,), "dtype": "f32"}
    entries = [
        ProbeTraceEntry(
            symbol=inner["symbol"], file=inner["file"],
            line=inner["line"], column=inner["column"],
            shape=inner["shape"], dtype=inner["dtype"],
        )
    ]
    collector = make_collector(probe_getter=lambda: entries)
    snapshot = collector.collect()
    # Clear the source list after collection
    entries.clear()
    # Snapshot must still contain the original entry
    assert len(snapshot.probed_traces) == 1
    assert snapshot.probed_traces[0].symbol == "sig"


# ── Robustness tests ──────────────────────────────────────────────────────────

def test_snapshot_does_not_raise_when_getter_returns_none():
    """If a getter returns None, the corresponding section is an empty tuple."""
    collector = make_collector(file_getter=lambda: None)
    snapshot = collector.collect()
    assert snapshot.open_files == ()


def test_snapshot_does_not_raise_when_getter_raises():
    """If a getter raises, the corresponding section is an empty tuple (no propagation)."""
    def broken():
        raise RuntimeError("GUI not ready")

    collector = make_collector(file_getter=broken)
    snapshot = collector.collect()  # must not raise
    assert snapshot.open_files == ()


# ── Path sanitization tests ───────────────────────────────────────────────────

def test_snapshot_paths_in_open_files_are_sanitized():
    """File paths in the snapshot have HOME replaced with <USER_HOME>."""
    from pathlib import Path
    home = str(Path.home())
    entry = OpenFileEntry(
        path=f"{home}/repos/script.py",
        is_probed=False, is_executed=True, has_unsaved=False,
    )
    snapshot = make_collector(file_getter=lambda: [entry]).collect()
    assert home not in snapshot.open_files[0].path
    assert "<USER_HOME>" in snapshot.open_files[0].path


def test_snapshot_paths_in_probe_sources_are_sanitized():
    """Probe source_file paths in the snapshot have HOME sanitized."""
    from pathlib import Path
    home = str(Path.home())
    entry = ProbeTraceEntry(
        symbol="sig", file=f"{home}/repos/script.py", line=1, column=1,
        shape=(64,), dtype="complex64",
    )
    snapshot = make_collector(probe_getter=lambda: [entry]).collect()
    assert home not in snapshot.probed_traces[0].file
    assert "<USER_HOME>" in snapshot.probed_traces[0].file


# ── Performance test ──────────────────────────────────────────────────────────

@pytest.mark.performance
def test_collect_is_fast_under_load():
    """collect() returns within 500 ms when getters return 1000 items each.

    Marked @pytest.mark.performance — exclude in constrained CI with:
        pytest -m 'not performance'
    """
    import time

    files = [
        OpenFileEntry(
            path=f"/tmp/file_{i}.py", is_probed=False, is_executed=True, has_unsaved=False
        )
        for i in range(1000)
    ]
    collector = make_collector(file_getter=lambda: files)

    start = time.monotonic()
    collector.collect()
    elapsed = time.monotonic() - start
    assert elapsed < 0.5, f"collect() took {elapsed:.3f}s, expected < 0.5s"
