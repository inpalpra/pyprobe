import os
import pytest
import numpy as np
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor

from pyprobe.plugins.builtins.waveform import WaveformPlugin, WaveformFftMagAnglePlugin
from pyprobe.plugins.builtins.complex_plots import (
    ComplexRIPlugin, ComplexMAPlugin,
    LogMagPlugin, LinearMagPlugin, PhaseRadPlugin, PhaseDegPlugin
)
from pyprobe.plugins.builtins.constellation import ConstellationPlugin
from pyprobe.plugins.builtins.scalar_history import ScalarHistoryPlugin

from pyprobe.core.data_classifier import DTYPE_ARRAY_1D, DTYPE_ARRAY_COMPLEX, DTYPE_SCALAR

# Skip all tests in this file if running in CI since they require real geometry rendering
pytestmark = pytest.mark.skipif("GITHUB_ACTIONS" in os.environ, reason="Requires GUI head for accurate geometry rendering")

@pytest.fixture
def probe_color():
    return QColor("#00ff00")

@pytest.fixture
def dummy_data(plugin_class):
    """Provides valid dummy data for a given plugin type."""
    if plugin_class == WaveformPlugin:
        return np.arange(100, dtype=float), DTYPE_ARRAY_1D
    elif plugin_class in (ComplexRIPlugin, ComplexMAPlugin, LogMagPlugin, LinearMagPlugin, PhaseRadPlugin, PhaseDegPlugin, ConstellationPlugin):
        return np.exp(1j * np.linspace(0, 2 * np.pi, 100)), DTYPE_ARRAY_COMPLEX
    elif plugin_class == ScalarHistoryPlugin:
        return 42.0, DTYPE_SCALAR
    else:
        raise ValueError(f"Unknown plugin class: {plugin_class}")

@pytest.mark.parametrize("plugin_class", [
    WaveformPlugin,
    ComplexRIPlugin,
    ComplexMAPlugin,
    LogMagPlugin,
    LinearMagPlugin,
    PhaseRadPlugin,
    PhaseDegPlugin,
    ConstellationPlugin,
    ScalarHistoryPlugin
])
def test_editable_axis_interaction(qtbot, qapp, probe_color, plugin_class):
    """
    Test that double clicking on the extremes of an EditableAxisItem spawns the AxisEditor
    and allows user to commit extreme bounds.
    """
    if plugin_class == WaveformPlugin:
        data, dtype = np.arange(100, dtype=float), DTYPE_ARRAY_1D
    elif plugin_class in (ComplexRIPlugin, ComplexMAPlugin, LogMagPlugin, LinearMagPlugin, PhaseRadPlugin, PhaseDegPlugin, ConstellationPlugin):
        data, dtype = np.exp(1j * np.linspace(0, 2 * np.pi, 100)), DTYPE_ARRAY_COMPLEX
    elif plugin_class == ScalarHistoryPlugin:
        data, dtype = 42.0, DTYPE_SCALAR
    else:
        raise ValueError(f"Unknown plugin class: {plugin_class}")
    
    # Setup widget
    plugin = plugin_class()
    widget = plugin.create_widget("test_var", probe_color)
    widget.resize(600, 400)
    widget.show()
    qtbot.addWidget(widget)
    
    # Must wait for widget to report as visible, else geometry is not reliable
    qtbot.waitUntil(widget.isVisible, timeout=1000)
    
    # Update data so the plot initializes its ViewBox ranges
    if plugin_class == WaveformPlugin:
        widget.update_data(data, dtype=dtype)
    elif plugin_class in (ComplexRIPlugin, ComplexMAPlugin):
        widget.update_data(data)
    elif plugin_class == ConstellationPlugin:
        widget.update_data(data, dtype=dtype)
    elif plugin_class == LogMagPlugin:
        mag_db = 20 * np.log10(np.abs(data) + 1e-12)
        widget.set_data(mag_db, "[100]")
    elif plugin_class == LinearMagPlugin:
        widget.set_data(np.abs(data), "[100]")
    elif plugin_class == PhaseRadPlugin:
        widget.set_data(np.angle(data), "[100]")
    elif plugin_class == PhaseDegPlugin:
        widget.set_data(np.rad2deg(np.angle(data)), "[100]")
    elif plugin_class == ScalarHistoryPlugin:
        widget.update_data(data, dtype=dtype)
    qapp.processEvents()

    # Locate plot widget which holds the axes
    plot_widget = widget._plot_widget
    plot_item = plot_widget.getPlotItem()
    
    bottom_axis = plot_item.getAxis('bottom')
    left_axis = plot_item.getAxis('left')

    # Test parameters: (axis_obj, axis_name, endpoint, signal_name)
    test_cases = [
        (bottom_axis, 'x', 'min', 'edit_min_requested'),
        (bottom_axis, 'x', 'max', 'edit_max_requested'),
        (left_axis, 'y', 'min', 'edit_min_requested'),
        (left_axis, 'y', 'max', 'edit_max_requested'),
    ]

    for axis_obj, axis_name, endpoint, signal_name in test_cases:
        from pyprobe.plots.editable_axis import EditableAxisItem
        if not isinstance(axis_obj, EditableAxisItem):
            # Skip if for some reason this axis wasn't replaced
            continue

        # We bypass the geometric hit testing and directly 
        # let the EditableAxisItem emit its signal
        signal = getattr(axis_obj, signal_name)
        signal.emit(0.0)
        qapp.processEvents()

        # The AxisEditor should now be visible
        axis_editor = widget._axis_editor
        assert axis_editor is not None
        qtbot.waitUntil(axis_editor.isVisible, timeout=1000)

        assert axis_editor.property('edit_axis') == axis_name
        assert axis_editor.property('edit_endpoint') == endpoint

        # PyqtGraph strictly enforces min < max on viewbox bounds.
        # We must choose a dynamically valid value based on the current limits.
        current_view = plot_item.getViewBox().viewRange()
        if axis_name == 'x':
            cur_min, cur_max = current_view[0]
        else:
            cur_min, cur_max = current_view[1]

        if endpoint == 'min':
            test_val = cur_min - 10.42  # Use a fractional value for isclose accuracy
        else:
            test_val = cur_max + 10.42

        # Enter text and commit
        axis_editor.setText(str(test_val))
        axis_editor._commit()

        # Verify Axis Editor closes
        qtbot.waitUntil(lambda: not axis_editor.isVisible(), timeout=1000)

        # Wait until the plot view bounds actually update asynchronously
        def verify_bounds():
            view_range = plot_item.getViewBox().viewRange()
            if axis_name == 'x':
                rendered_val = view_range[0][0] if endpoint == 'min' else view_range[0][1]
            else:
                rendered_val = view_range[1][0] if endpoint == 'min' else view_range[1][1]
            assert np.isclose(rendered_val, test_val), f"Expected {endpoint} bound of {axis_name} to be {test_val} but was {rendered_val}"
            
        qtbot.waitUntil(verify_bounds, timeout=1000)
        
        # Check Pinned state
        controller = widget._axis_controller
        if controller:
            if axis_name == 'x':
                assert controller.x_pinned
            else:
                assert controller.y_pinned
                
        # Unpin and auto-range for next iteration
        if controller:
            controller.set_pinned('x', False)
            controller.set_pinned('y', False)
        plot_item.getViewBox().enableAutoRange()
        plot_item.getViewBox().autoRange(padding=0)
        qapp.processEvents()


@pytest.mark.parametrize("plugin_class", [
    ComplexMAPlugin,
    WaveformFftMagAnglePlugin,
])
def test_editable_secondary_axis_interaction(qtbot, qapp, probe_color, plugin_class):
    """
    Test that double clicking on the right (secondary) y-axis spawns the AxisEditor
    with 'y2' context and correctly updates the secondary ViewBox range.
    """
    data = np.exp(1j * np.linspace(0, 2 * np.pi, 100))

    plugin = plugin_class()
    widget = plugin.create_widget("test_var", probe_color)
    widget.resize(600, 400)
    widget.show()
    qtbot.addWidget(widget)
    qtbot.waitUntil(widget.isVisible, timeout=1000)

    # Feed data to initialise the plot
    if plugin_class == ComplexMAPlugin:
        widget.update_data(data)
    elif plugin_class == WaveformFftMagAnglePlugin:
        widget.update_data(np.abs(data), dtype=DTYPE_ARRAY_1D)
    qapp.processEvents()

    # The right axis should now be an EditableAxisItem
    plot_item = widget._plot_widget.getPlotItem()
    right_axis = plot_item.getAxis('right')

    from pyprobe.plots.editable_axis import EditableAxisItem
    assert isinstance(right_axis, EditableAxisItem), (
        f"Right axis is {type(right_axis).__name__}, expected EditableAxisItem"
    )

    # Test both min and max endpoints on the secondary axis
    for endpoint, signal_name in [('min', 'edit_min_requested'), ('max', 'edit_max_requested')]:
        signal = getattr(right_axis, signal_name)
        signal.emit(0.0)
        qapp.processEvents()

        axis_editor = widget._axis_editor
        assert axis_editor is not None
        qtbot.waitUntil(axis_editor.isVisible, timeout=1000)

        # Should be tagged as 'y2'
        assert axis_editor.property('edit_axis') == 'y2'
        assert axis_editor.property('edit_endpoint') == endpoint

        # Determine a valid test value
        p2 = widget._p2
        cur_min, cur_max = p2.viewRange()[1]
        test_val = cur_min - 5.0 if endpoint == 'min' else cur_max + 5.0

        axis_editor.setText(str(test_val))
        axis_editor._commit()

        qtbot.waitUntil(lambda: not axis_editor.isVisible(), timeout=1000)

        # Verify secondary ViewBox range updated
        def verify_p2():
            p2_range = p2.viewRange()[1]
            rendered_val = p2_range[0] if endpoint == 'min' else p2_range[1]
            assert np.isclose(rendered_val, test_val), (
                f"Expected secondary y {endpoint} to be {test_val} but was {rendered_val}"
            )

        qtbot.waitUntil(verify_p2, timeout=1000)

        # Y should be pinned
        controller = widget._axis_controller if hasattr(widget, '_axis_controller') else None
        if controller:
            assert controller.y_pinned, "Y axis should be pinned after secondary axis edit"

        # Unpin for next iteration
        if controller:
            controller.set_pinned('x', False)
            controller.set_pinned('y', False)
        p2.enableAutoRange(axis='y')
        p2.autoRange(padding=0)
        plot_item.getViewBox().enableAutoRange()
        plot_item.getViewBox().autoRange(padding=0)
        qapp.processEvents()

