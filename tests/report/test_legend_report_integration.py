
import pytest
import numpy as np
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication
import pyqtgraph as pg

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.gui.probe_panel import ProbePanel
from pyprobe.gui.probe_registry import ProbeRegistry
from pyprobe.report.formatter import ReportFormatter
from pyprobe.report.session_snapshot import SessionStateCollector
from pyprobe.report.report_model import BugReport
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D

@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])

def test_legend_extraction_to_report(qapp, qtbot):
    """
    Regression test: verify that legend entries from a real UI plot 
    are correctly extracted and rendered in the bug report.
    """
    registry = ProbeRegistry()
    anchor = ProbeAnchor(file="test.py", line=10, col=5, symbol="sig")
    
    # 1. Create a panel and initialize it with array data to trigger WaveformWidget
    panel = ProbePanel(anchor, QColor("cyan"), DTYPE_ARRAY_1D, trace_id="tr0", window_id="w1")
    qtbot.addWidget(panel)
    panel.show()
    panel.update_data(np.array([1, 2, 3]), DTYPE_ARRAY_1D)
    
    # 2. Manually add an entry to the legend to simulate an overlay or multi-row signal
    # WaveformWidget creates a legend during _setup_ui if theme is set.
    if panel._plot and hasattr(panel._plot, '_legend') and panel._plot._legend:
        # Create a dummy curve to add to legend
        dummy_curve = pg.PlotDataItem(name="Overlay Trace")
        panel._plot._legend.addItem(dummy_curve, "tr1: Overlay Trace")
    
    # 3. Use the Collector to get the baseline state
    collector = SessionStateCollector(
        file_getter=lambda: [],
        probe_getter=lambda: [],
        equation_getter=lambda: [],
        widget_getter=lambda: [panel.get_report_entry(registry, is_docked=True)]
    )
    
    baseline = collector.collect()
    report = BugReport(description="Legend test", baseline_state=baseline)
    
    # 4. Render the report
    formatter = ReportFormatter()
    output = formatter.render(report)
    
    # 5. Verify the window section format and legends
    print("\n--- Rendered Window Section ---")
    if "Windows:" in output:
        window_section = output.split("Windows:")[1]
        print(window_section)
        
        assert "w1 [Waveform, docked, visible]:" in window_section
        assert "plotted:  tr0  [tr0.val]" in window_section
        assert "legends:" in window_section
        assert "- tr1: Overlay Trace" in window_section
    else:
        pytest.fail("Windows section missing from report")
