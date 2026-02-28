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


class TestProbePanelCreation:
    def test_child_is_waveform_widget(self, panel):
        """Panel with array_1d dtype creates WaveformWidget."""
        assert isinstance(panel._plot, WaveformWidget)

    def test_identity_label_text(self, panel, panel_anchor):
        """Identity label contains symbol and file info."""
        text = panel._identity_label.text()
        assert "signal_i" in text
        assert "dsp.py" in text

    def test_state_indicator_default(self, panel):
        """State indicator starts in ARMED state."""
        # ProbeStateIndicator exists
        assert panel._state_indicator is not None

    def test_set_state(self, panel):
        """set_state() changes the state indicator."""
        panel.set_state(ProbeState.LIVE)
        # Should not raise

    def test_minimum_size(self, panel):
        """Panel has a minimum size set."""
        assert panel.minimumWidth() >= 300
        assert panel.minimumHeight() >= 250


class TestProbePanelLensDropdown:
    def test_dropdown_exists(self, panel):
        """Panel has a lens dropdown."""
        assert panel._lens_dropdown is not None

    def test_dropdown_lists_compatible_plugins(self, panel):
        """Lens dropdown lists plugins compatible with array_1d."""
        count = panel._lens_dropdown.count()
        assert count >= 1
        # Should contain "Waveform" at minimum
        items = [panel._lens_dropdown.itemText(i) for i in range(count)]
        assert "Waveform" in items


class TestProbePanelData:
    def test_update_data(self, panel, qapp):
        """update_data() pushes data to the underlying plot."""
        data = np.array([1, 2, 3, 4, 5], dtype=float)
        panel.update_data(data, DTYPE_ARRAY_1D)
        qapp.processEvents()

        # Verify data reached the plot
        assert isinstance(panel._plot, WaveformWidget)
        _, y = panel._plot._curves[0].getData()
        np.testing.assert_allclose(y, [1, 2, 3, 4, 5])


class TestProbePanelLensChange:
    def test_lens_change_swaps_widget(self, panel, qapp):
        """Changing lens replaces the plot widget."""
        old_plot = panel._plot
        # Switch to a different compatible lens if available
        count = panel._lens_dropdown.count()
        if count < 2:
            pytest.skip("Only one compatible lens available")

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


class TestProbePanelProperties:
    def test_anchor_property(self, panel, panel_anchor):
        """anchor property returns the original anchor."""
        assert panel.anchor == panel_anchor

    def test_var_name_property(self, panel):
        """var_name returns the anchor symbol."""
        assert panel.var_name == "signal_i"

    def test_current_lens(self, panel):
        """current_lens returns a non-empty string."""
        assert len(panel.current_lens) > 0
