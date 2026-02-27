
import pytest
import numpy as np

# Skip all tests in this file if running in CI since they require real geometry rendering
import os
pytestmark = pytest.mark.skipif("GITHUB_ACTIONS" in os.environ, reason="Requires GUI head for accurate geometry rendering")

from pyprobe.gui.main_window import MainWindow
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D, DTYPE_ARRAY_COMPLEX

@pytest.fixture
def win(qapp):
    """Create a MainWindow for testing."""
    window = MainWindow()
    window.resize(1200, 800)
    window.show()
    qapp.processEvents()
    yield window
    window.close()
    qapp.processEvents()

def test_fft_overlay_legend_e2e(win, qapp):
    """
    E2E Test: 
    1. Probe 'sig_main' (complex data)
    2. Probe 'sig_ov' (real data)
    3. Feed data for both
    4. Overlay 'sig_ov' onto 'sig_main'
    5. Switch 'sig_main' lens to 'FFT Mag & Phase'
    6. Verify overlay legend entry is present and traces are not disjoint.
    """
    anchor_main = ProbeAnchor(file="/tmp/test.py", line=10, col=0, symbol="sig_main")
    anchor_ov = ProbeAnchor(file="/tmp/test.py", line=20, col=0, symbol="sig_ov")
    
    # 1. Add probes
    win._on_probe_requested(anchor_main)
    win._on_probe_requested(anchor_ov)
    qapp.processEvents()
    
    # 2. Feed data
    win._on_probe_value({
        'anchor': anchor_main.to_dict(),
        'value': np.random.randn(100) + 1j*np.random.randn(100),
        'dtype': DTYPE_ARRAY_COMPLEX
    })
    win._on_probe_value({
        'anchor': anchor_ov.to_dict(),
        'value': np.random.randn(100),
        'dtype': DTYPE_ARRAY_1D
    })
    qapp.processEvents()
    
    # Verify panels created
    assert anchor_main in win._probe_panels
    assert anchor_ov in win._probe_panels
    panel_main = win._probe_panels[anchor_main][0]
    
    # 3. Add overlay
    win._probe_controller.handle_overlay_requested(panel_main, anchor_ov)
    # Controller must forward data to apply the overlay visually
    win._probe_controller.forward_overlay_data(anchor_ov, {
        'value': np.random.randn(100),
        'dtype': DTYPE_ARRAY_1D
    })
    qapp.processEvents()
    
    # 4. Switch lens to FFT
    panel_main._lens_dropdown.set_lens("FFT Mag & Phase")
    qapp.processEvents()
    
    # 5. Verify Legend
    legend = panel_main._plot._legend
    labels = [label.text if hasattr(label, 'text') else str(label) for _, label in legend.items]
    print(f"Legend labels: {labels}")
    
    main_id = win._probe_registry.get_trace_id(anchor_main)
    ov_id = win._probe_registry.get_trace_id(anchor_ov)
    
    mag_label = f"{main_id}: sig_main (fft_mag_db)"
    phase_label = f"{main_id}: sig_main (fft_angle_deg)"
    ov_label = f"{ov_id}: sig_ov"
    
    assert mag_label in labels
    assert phase_label in labels
    assert ov_label in labels, f"Overlay '{ov_label}' missing from FFT legend after lens switch. Found: {labels}"
    
    # Verify order: Mag and Phase should be adjacent, or Overlay at the end.
    mag_idx = labels.index(mag_label)
    phase_idx = labels.index(phase_label)
    ov_idx = labels.index(ov_label)
    
    assert abs(mag_idx - phase_idx) == 1, f"Primary components should be adjacent. Labels: {labels}"
    
    # 6. Verify format in report
    entries = win._probe_container.graph_widget_entries(win._probe_registry)
    
    # Find the widget in the report state
    widget_entry = None
    for w in entries:
        if w.widget_id == panel_main.window_id:
            widget_entry = w
            break
            
    assert widget_entry is not None
    assert widget_entry.lens == "FFT Mag & Phase"
    
    # Verify primary trace components
    assert "tr0.fft_mag_db" in widget_entry.primary_trace.components
    assert "tr0.fft_angle_deg" in widget_entry.primary_trace.components
    
    # Verify overlay traces
    assert len(widget_entry.overlay_traces) == 1
    assert widget_entry.overlay_traces[0].trace_id == ov_id
    assert widget_entry.overlay_traces[0].components == ("tr1.val",)
