import pytest
from pyprobe.report.report_model import (
    WidgetTraceEntry, GraphWidgetEntry, ProbeTraceEntry, RecordedStep
)

def test_widget_trace_entry():
    entry = WidgetTraceEntry(trace_id="tr1", components=("tr1.real", "tr1.imag"))
    assert entry.trace_id == "tr1"
    assert entry.components == ("tr1.real", "tr1.imag")

def test_graph_widget_entry():
    primary = WidgetTraceEntry(trace_id="tr0", components=("tr0.val",))
    overlay = WidgetTraceEntry(trace_id="tr1", components=("tr1.real", "tr1.imag"))
    
    entry = GraphWidgetEntry(
        widget_id="w0",
        is_docked=True,
        is_visible=True,
        lens="Waveform",
        primary_trace=primary,
        overlay_traces=(overlay,)
    )
    
    assert entry.widget_id == "w0"
    assert entry.lens == "Waveform"
    assert entry.primary_trace == primary
    assert entry.overlay_traces[0] == overlay

def test_probe_trace_entry():
    entry = ProbeTraceEntry(
        symbol="signal_i",
        file="dsp_demo.py",
        line=42,
        column=4,
        shape=(1000,),
        dtype="float64"
    )
    
    assert entry.symbol == "signal_i"
    assert entry.line == 42
    assert entry.column == 4

def test_recorded_step():
    step = RecordedStep(
        seq_num=1,
        timestamp=100.0,
        action_type="Click",
        target_element="PLOT__X_AXIS_LINE",
        modifiers=("Alt",),
        button="Left",
        description="Alt-clicked X axis"
    )
    
    assert step.action_type == "Click"
    assert step.target_element == "PLOT__X_AXIS_LINE"
    assert step.modifiers == ("Alt",)
    assert step.button == "Left"
