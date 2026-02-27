import pytest
from PyQt6.QtGui import QColor
from pyprobe.gui.probe_panel import ProbePanel
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D, DTYPE_ARRAY_COMPLEX
from unittest.mock import MagicMock

def test_get_report_entry_primary_only(qapp):
    anchor = ProbeAnchor(file="test.py", line=1, col=1, symbol="sig")
    panel = ProbePanel(anchor, QColor("red"), DTYPE_ARRAY_1D, trace_id="tr0", window_id="w0")
    
    registry = MagicMock()
    entry = panel.get_report_entry(registry, is_docked=True)
    
    assert entry.widget_id == "w0"
    assert entry.is_docked is True
    assert entry.primary_trace.trace_id == "tr0"
    assert entry.primary_trace.components == ("tr0.val",)
    assert len(entry.overlay_traces) == 0

def test_get_report_entry_with_overlays(qapp):
    anchor = ProbeAnchor(file="test.py", line=1, col=1, symbol="sig")
    panel = ProbePanel(anchor, QColor("red"), DTYPE_ARRAY_1D, trace_id="tr0", window_id="w0")
    
    overlay_anchor = ProbeAnchor(file="test.py", line=2, col=1, symbol="ovl")
    panel._overlay_anchors = [overlay_anchor]
    
    registry = MagicMock()
    registry.get_trace_id.return_value = "tr1"
    
    entry = panel.get_report_entry(registry, is_docked=False)
    
    assert entry.is_docked is False
    assert entry.primary_trace.trace_id == "tr0"
    assert len(entry.overlay_traces) == 1
    assert entry.overlay_traces[0].trace_id == "tr1"
    assert entry.overlay_traces[0].components == ("tr1.val",)

def test_get_report_entry_complex_lens(qapp):
    anchor = ProbeAnchor(file="test.py", line=1, col=1, symbol="sig")
    # Using complex data to get complex lenses
    panel = ProbePanel(anchor, QColor("red"), DTYPE_ARRAY_COMPLEX, trace_id="tr0", window_id="w0")
    
    # Force "Real & Imag" lens
    panel._lens_dropdown.set_lens("Real & Imag")
    
    registry = MagicMock()
    entry = panel.get_report_entry(registry, is_docked=True)
    
    assert entry.lens == "Real & Imag"
    assert entry.primary_trace.components == ("tr0.real", "tr0.imag")

def test_get_report_entry_mag_phase_lens(qapp):
    anchor = ProbeAnchor(file="test.py", line=1, col=1, symbol="sig")
    panel = ProbePanel(anchor, QColor("red"), DTYPE_ARRAY_COMPLEX, trace_id="tr0", window_id="w0")
    
    # Force "Mag & Phase" lens
    panel._lens_dropdown.set_lens("Mag & Phase")
    
    registry = MagicMock()
    entry = panel.get_report_entry(registry, is_docked=True)
    
    assert entry.lens == "Mag & Phase"
    assert entry.primary_trace.components == ("tr0.mag_db", "tr0.phase_deg")
