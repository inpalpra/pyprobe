"""
Factory for creating appropriate plot widgets based on data type.

DEPRECATED: The primary widget creation path now uses PluginRegistry.
This module is retained as a fallback for edge cases.
"""

from typing import Optional
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QColor

from .base_plot import BasePlot
from ..plugins.builtins.waveform import WaveformWidget
from .constellation import ConstellationPlot
from .scalar_history_chart import ScalarHistoryChart
from ..core.data_classifier import (
    DTYPE_SCALAR, DTYPE_ARRAY_1D, DTYPE_ARRAY_COMPLEX,
    DTYPE_ARRAY_2D, DTYPE_ARRAY_COLLECTION,
    DTYPE_WAVEFORM_REAL, DTYPE_WAVEFORM_COMPLEX,
    DTYPE_WAVEFORM_COLLECTION, DTYPE_UNKNOWN
)


def create_plot(
    var_name: str,
    dtype: str,
    parent: Optional[QWidget] = None
) -> QWidget:
    """Create a plot widget for the given data type.
    
    DEPRECATED: Use PluginRegistry.get_default_plugin() instead.
    This factory is retained as a fallback for edge cases.
    """
    # Default color for fallback widgets (cyan)
    default_color = QColor('#00ffff')
    
    if dtype == DTYPE_ARRAY_COMPLEX:
        return ConstellationPlot(var_name, parent)
    elif dtype == DTYPE_ARRAY_1D:
        return WaveformWidget(var_name, default_color, parent)
    elif dtype == DTYPE_WAVEFORM_REAL:
        return WaveformWidget(var_name, default_color, parent)
    elif dtype == DTYPE_WAVEFORM_COMPLEX:
        return ConstellationPlot(var_name, parent)
    elif dtype == DTYPE_WAVEFORM_COLLECTION:
        return WaveformWidget(var_name, default_color, parent)
    elif dtype == DTYPE_ARRAY_COLLECTION:
        return WaveformWidget(var_name, default_color, parent)
    elif dtype == DTYPE_ARRAY_2D:
        # For now, use waveform plot (flattened) for 2D arrays
        return WaveformWidget(var_name, default_color, parent)
    elif dtype == DTYPE_SCALAR:
        return ScalarHistoryChart(var_name, parent)
    else:
        # Unknown type - default to scalar history chart
        return ScalarHistoryChart(var_name, parent)


def get_plot_type_name(dtype: str) -> str:
    """Get human-readable name for a plot type."""
    type_names = {
        DTYPE_SCALAR: "Scalar",
        DTYPE_ARRAY_1D: "Waveform",
        DTYPE_ARRAY_COMPLEX: "Constellation",
        DTYPE_ARRAY_2D: "2D Array",
        DTYPE_ARRAY_COLLECTION: "Array Collection",
        DTYPE_WAVEFORM_REAL: "Waveform",
        DTYPE_WAVEFORM_COMPLEX: "Complex Waveform",
        DTYPE_WAVEFORM_COLLECTION: "Waveform Collection",
        DTYPE_UNKNOWN: "Unknown",
    }
    return type_names.get(dtype, "Unknown")
