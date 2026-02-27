import json
import os
import jsonschema
import pytest

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '../../pyprobe/report/report_schema.json')

@pytest.fixture
def schema():
    with open(SCHEMA_PATH, 'r') as f:
        return json.load(f)

def test_schema_is_valid(schema):
    """Test that the schema itself is a valid JSON schema draft-2020-12."""
    jsonschema.Draft202012Validator.check_schema(schema)

def test_valid_report_payload(schema):
    """Test that a compliant payload validates successfully."""
    payload = {
        "description": "User dragged the x-axis",
        "environment": {"os": "darwin"},
        "baseline_state": {
            "open_files": [
                {
                    "path": "/path/to/script.py",
                    "is_probed": True,
                    "is_executed": True,
                    "has_unsaved": False,
                    "contents": "print('hello')"
                }
            ],
            "probes": [
                {
                    "symbol": "signal_i",
                    "file": "/path/to/script.py",
                    "line": 42,
                    "column": 4,
                    "shape": [1000],
                    "dtype": "float64"
                }
            ],
            "equations": [],
            "graph_widgets": [
                {
                    "widget_id": "w0",
                    "is_docked": True,
                    "is_visible": True,
                    "lens": "Waveform",
                    "primary_trace": {
                        "trace_id": "tr0",
                        "components": ["tr0.val"]
                    },
                    "overlay_traces": [
                        {
                            "trace_id": "tr1",
                            "components": ["tr1.real", "tr1.imag"]
                        }
                    ]
                }
            ],
            "captured_at": 1678886400.0
        },
        "steps": [
            {
                "seq_num": 1,
                "timestamp": 1678886405.0,
                "action_type": "Scroll",
                "target_element": "PLOT__X_AXIS_LINE",
                "modifiers": [],
                "button": "None",
                "description": "Two-finger drag on X axis"
            }
        ],
        "logs": None
    }
    jsonschema.validate(instance=payload, schema=schema)

def test_invalid_report_payload(schema):
    """Test that a missing required field causes validation to fail."""
    payload = {
        "description": "Missing baseline_state",
        "steps": []
    }
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=payload, schema=schema)
