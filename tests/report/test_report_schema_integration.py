import json
import os
import jsonschema
import pytest
from pyprobe.report.report_model import (
    BugReport, SessionState, ProbeTraceEntry, GraphWidgetEntry, WidgetTraceEntry, RecordedStep
)
from pyprobe.report.formatter import ReportFormatter

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '../../pyprobe/report/report_schema.json')

@pytest.fixture
def schema():
    with open(SCHEMA_PATH, 'r') as f:
        return json.load(f)

def test_full_report_json_schema_validation(schema):
    formatter = ReportFormatter()
    
    probe = ProbeTraceEntry(
        symbol="sig", file="test.py", line=10, column=5, shape=(100,), dtype="float64"
    )
    primary = WidgetTraceEntry(trace_id="tr0", components=("tr0.val",))
    widget = GraphWidgetEntry(
        widget_id="w0", is_docked=True, is_visible=True, lens="Waveform",
        primary_trace=primary, overlay_traces=()
    )
    
    state = SessionState(
        open_files=(),
        probed_traces=(probe,),
        equations=(),
        graph_widgets=(widget,),
        captured_at=123456789.0
    )
    
    step = RecordedStep(
        seq_num=1,
        timestamp=123456790.0,
        action_type="Click",
        target_element="W0__LEGEND",
        modifiers=(),
        button="Left",
        description="Clicked legend"
    )
    
    report = BugReport(
        description="Test schema integration",
        baseline_state=state,
        steps=(step,),
        environment={"os": "darwin"}
    )
    
    json_text = formatter.render_json(report)
    payload = json.loads(json_text)
    
    # This will raise jsonschema.exceptions.ValidationError if it fails
    jsonschema.validate(instance=payload, schema=schema)
