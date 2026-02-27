import pytest
from PyQt6.QtCore import QObject, pyqtSignal
from pyprobe.report.step_recorder import StepRecorder
from pyprobe.core.anchor import ProbeAnchor

class MockController(QObject):
    panel_trace_visibility_changed = pyqtSignal(object, str, str, bool)

def _make_anchor(symbol="signal_q", line=12, col=4):
    return ProbeAnchor(
        file="dsp_demo.py", line=line, col=col,
        symbol=symbol, func="", is_assignment=False,
    )

def test_legend_toggle_records_step():
    """Start recording, emit panel_trace_visibility_changed, assert step recorded."""
    recorder = StepRecorder()
    controller = MockController()
    anchor = _make_anchor("signal_i", line=10, col=2)
    
    # Wire the signal as it is in MainWindow
    recorder.connect_signal(
        controller.panel_trace_visibility_changed,
        lambda anchor, wid, name, visible: f"Toggled visibility of {name} in window {wid} ({anchor.identity_label()})")
    
    recorder.start()
    controller.panel_trace_visibility_changed.emit(anchor, "w0", "Phase", False)
    steps = recorder.stop()
    
    assert len(steps) == 1
    assert steps[0].description == "Toggled visibility of Phase in window w0 (signal_i @ dsp_demo.py:10:2)"

def test_legend_toggle_records_once_per_click():
    """Verify exactly one step recorded per signal emission."""
    recorder = StepRecorder()
    controller = MockController()
    anchor = _make_anchor()
    
    recorder.connect_signal(
        controller.panel_trace_visibility_changed,
        lambda a, wid, n, v: f"Toggled {n}")
    
    recorder.start()
    controller.panel_trace_visibility_changed.emit(anchor, "w0", "Phase", False)
    steps = recorder.stop()
    assert len(steps) == 1

def test_legend_toggle_not_recorded_when_not_recording():
    """Emit signal without starting recording — verify zero steps."""
    recorder = StepRecorder()
    controller = MockController()
    
    recorder.connect_signal(
        controller.panel_trace_visibility_changed,
        lambda a, wid, n, v: "should not appear")
    
    controller.panel_trace_visibility_changed.emit(_make_anchor(), "w0", "Phase", False)
    # StepRecorder.stop() returns empty if never started or cleared
    assert len(recorder.stop()) == 0

def test_toggle_message_contains_window_id_and_anchor():
    """Ensure window id and identity_label appear in step text."""
    recorder = StepRecorder()
    controller = MockController()
    anchor = _make_anchor("received_symbols", line=72, col=8)
    
    recorder.connect_signal(
        controller.panel_trace_visibility_changed,
        lambda anchor, wid, name, visible: f"Toggled visibility of {name} in window {wid} ({anchor.identity_label()})")
    
    recorder.start()
    controller.panel_trace_visibility_changed.emit(anchor, "w0", "Phase", False)
    steps = recorder.stop()
    
    assert "Phase" in steps[0].description
    assert "window w0" in steps[0].description
    assert "received_symbols @ dsp_demo.py:72:8" in steps[0].description
