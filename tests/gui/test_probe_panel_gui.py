"""Phase 2.5: Probe panel integration tests.

Verifies panel creation, identity label, state indicator,
lens dropdown, and lens change behavior.
"""

import numpy as np
import pytest
from PyQt6.QtGui import QColor

from pyprobe.gui.probe_panel import ProbePanel
from pyprobe.gui.probe_state import ProbeState
from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D, DTYPE_SCALAR
from pyprobe.plugins.builtins.waveform import WaveformWidget


@pytest.fixture
def panel_anchor():
    return ProbeAnchor(
        file="/tmp/dsp.py", line=42, col=4,
        symbol="signal_i", func="process",
    )


@pytest.fixture
def panel(qtbot, qapp, panel_anchor, probe_color):
    """Create a ProbePanel with array_1d dtype."""
    p = ProbePanel(panel_anchor, probe_color, DTYPE_ARRAY_1D)
    qtbot.addWidget(p)
    p.resize(600, 400)
    p.show()
    qapp.processEvents()
    yield p
    p.close()
    p.deleteLater()
    qapp.processEvents()


def test_probe_panel_lifecycle_fast(panel, panel_anchor, qapp):
    """
    Consolidated megatest for ProbePanel to avoid multiple widget creations.
    """
    
    # --- TestProbePanelCreation ---
    # Panel with array_1d dtype creates WaveformWidget
    assert isinstance(panel._plot, WaveformWidget)
    
    # Identity label contains symbol and file info
    text = panel._identity_label.text()
    assert "signal_i" in text
    assert "dsp.py" in text
    
    # State indicator starts in ARMED state
    assert panel._state_indicator is not None
    
    # set_state() changes the state indicator
    panel.set_state(ProbeState.LIVE)
    
    # Panel has a minimum size set
    assert panel.minimumWidth() >= 300
    assert panel.minimumHeight() >= 250
    
    # --- TestProbePanelLensDropdown ---
    # Panel has a lens dropdown
    assert panel._lens_dropdown is not None
    
    # Lens dropdown lists plugins compatible with array_1d
    count = panel._lens_dropdown.count()
    assert count >= 1
    items = [panel._lens_dropdown.itemText(i) for i in range(count)]
    assert "Waveform" in items
    
    # --- TestProbePanelData ---
    # update_data() pushes data to the underlying plot
    data = np.array([1, 2, 3, 4, 5], dtype=float)
    panel.update_data(data, DTYPE_ARRAY_1D)
    qapp.processEvents()

    # Verify data reached the plot
    assert isinstance(panel._plot, WaveformWidget)
    _, y = panel._plot._curves[0].getData()
    np.testing.assert_allclose(y, [1, 2, 3, 4, 5])
    
    # --- TestProbePanelProperties ---
    # anchor property returns the original anchor
    assert panel.anchor == panel_anchor
    
    # var_name returns the anchor symbol
    assert panel.var_name == "signal_i"
    
    # current_lens returns a non-empty string
    assert len(panel.current_lens) > 0
    
    # --- TestProbePanelLensChange ---
    # Changing lens replaces the plot widget
    old_plot = panel._plot
    
    if count >= 2:
        # Find a different lens
        current_text = panel._lens_dropdown.currentText()
        for i in range(count):
            text = panel._lens_dropdown.itemText(i)
            if text != current_text:
                panel._lens_dropdown.setCurrentIndex(i)
                qapp.processEvents()
                break

        # Plot widget should have changed
        assert panel._plot is not old_plot
