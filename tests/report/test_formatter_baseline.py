import pytest
from pyprobe.report.report_model import (
    BugReport, SessionState, ProbeTraceEntry, GraphWidgetEntry, WidgetTraceEntry
)
from pyprobe.report.formatter import ReportFormatter

def test_render_baseline_probes():
    formatter = ReportFormatter()
    probe = ProbeTraceEntry(
        symbol="sig", file="test.py", line=10, column=5, shape=(100,), dtype="float64"
    )
    state = SessionState(probed_traces=(probe,))
    report = BugReport(description="Test baseline.", baseline_state=state)
    
    output = formatter.render(report)
    assert "sig @ test.py:10:5 (float64, shape=(100,))" in output

def test_render_baseline_widgets():
    formatter = ReportFormatter()
    primary = WidgetTraceEntry(trace_id="tr0", components=("tr0.val",))
    widget = GraphWidgetEntry(
        widget_id="w0", is_docked=True, is_visible=True, lens="Waveform",
        primary_trace=primary, overlay_traces=(), legend_entries=("Trace 0",)
    )
    state = SessionState(graph_widgets=(widget,))
    report = BugReport(description="Test widgets.", baseline_state=state)
    
    output = formatter.render(report)
    assert "w0 [Waveform, docked, visible]:" in output
    assert "plotted:  tr0  [tr0.val]" in output
    assert "legends:" in output
    assert "- Trace 0" in output

def test_render_json_baseline():
    formatter = ReportFormatter()
    probe = ProbeTraceEntry(
        symbol="sig", file="test.py", line=10, column=5, shape=(100,), dtype="float64"
    )
    primary = WidgetTraceEntry(trace_id="tr0", components=("tr0.val",))
    widget = GraphWidgetEntry(
        widget_id="w0", is_docked=True, is_visible=True, lens="Waveform",
        primary_trace=primary, overlay_traces=(), legend_entries=("Trace 0",)
    )
    state = SessionState(probed_traces=(probe,), graph_widgets=(widget,))
    report = BugReport(description="Test json.", baseline_state=state)
    
    import json
    output = formatter.render_json(report)
    parsed = json.loads(output)
    
    p = parsed["baseline_state"]["probes"][0]
    assert p["symbol"] == "sig"
    assert p["file"] == "test.py"
    assert p["line"] == 10
    assert p["column"] == 5
    
    w = parsed["baseline_state"]["graph_widgets"][0]
    assert w["widget_id"] == "w0"
    assert w["lens"] == "Waveform"
    assert w["primary_trace"]["trace_id"] == "tr0"
    assert w["primary_trace"]["components"] == ["tr0.val"]
    assert w["legend_entries"] == ["Trace 0"]
