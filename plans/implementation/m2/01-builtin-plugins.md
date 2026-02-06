# Plan 1: Builtin Plugins

**Focus:** Refactor existing plot widgets to implement the `ProbePlugin` interface.

**Branch:** `m2/builtin-plugins`

**Dependencies:** Plan 0 (ProbePlugin ABC)

**Complexity:** Medium (M)

---

## Overview

Convert existing plots from `BasePlot` subclasses to `ProbePlugin` implementations.

**Current structure:**
```
pyprobe/plots/
├── base_plot.py           # OLD ABC (will be deprecated)
├── waveform_plot.py       # WaveformPlot(BasePlot)
├── constellation.py       # ConstellationPlot(BasePlot)
├── scalar_history_chart.py # ScalarHistoryChart(BasePlot)
├── scalar_display.py      # ScalarDisplay(BasePlot)
└── plot_factory.py        # OLD factory (will be deprecated)
```

**New structure:**
```
pyprobe/plugins/builtins/
├── __init__.py            # get_builtin_plugins()
├── waveform.py            # WaveformPlugin
├── constellation.py       # ConstellationPlugin
├── scalar_history.py      # ScalarHistoryPlugin
└── scalar_display.py      # ScalarDisplayPlugin
```

---

## Files to Create

### `pyprobe/plugins/builtins/waveform.py`
```python
"""Waveform visualization plugin for 1D arrays."""
from typing import Any, Optional, Tuple
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QFont, QColor

from ..base import ProbePlugin
from ...core.data_classifier import DTYPE_ARRAY_1D, DTYPE_ARRAY_2D


class WaveformWidget(QWidget):
    """The actual plot widget created by WaveformPlugin."""
    
    MAX_DISPLAY_POINTS = 5000
    
    def __init__(self, var_name: str, color: QColor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._var_name = var_name
        self._color = color
        self._data: Optional[np.ndarray] = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the plot widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Header with variable name
        header = QHBoxLayout()
        self._name_label = QLabel(self._var_name)
        self._name_label.setFont(QFont("JetBrains Mono", 11, QFont.Weight.Bold))
        self._name_label.setStyleSheet(f"color: {self._color.name()};")
        header.addWidget(self._name_label)
        header.addStretch()
        self._info_label = QLabel("")
        self._info_label.setFont(QFont("JetBrains Mono", 9))
        self._info_label.setStyleSheet("color: #888888;")
        header.addWidget(self._info_label)
        layout.addLayout(header)
        
        # PyQtGraph plot
        self._plot_widget = pg.PlotWidget()
        self._configure_plot()
        layout.addWidget(self._plot_widget)
        
        # Stats bar
        self._stats_label = QLabel("Min: -- | Max: -- | Mean: --")
        self._stats_label.setFont(QFont("JetBrains Mono", 9))
        self._stats_label.setStyleSheet(f"color: {self._color.name()};")
        layout.addWidget(self._stats_label)
    
    def _configure_plot(self):
        """Configure plot appearance using probe color."""
        self._plot_widget.setBackground('#0d0d0d')
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.useOpenGL(False)
        
        axis_pen = pg.mkPen(color=self._color.name(), width=1)
        self._plot_widget.getAxis('left').setPen(axis_pen)
        self._plot_widget.getAxis('bottom').setPen(axis_pen)
        self._plot_widget.getAxis('left').setTextPen(axis_pen)
        self._plot_widget.getAxis('bottom').setTextPen(axis_pen)
        
        # Use probe color for the curve
        self._curve = self._plot_widget.plot(
            pen=pg.mkPen(color=self._color.name(), width=1.5),
            antialias=False
        )
    
    # ... rest of waveform implementation (downsample, stats, etc.)
    # Copy logic from existing waveform_plot.py


class WaveformPlugin(ProbePlugin):
    """Plugin for visualizing 1D arrays as waveforms."""
    
    name = "Waveform"
    icon = "waveform"
    priority = 100  # High priority for 1D arrays
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype in (DTYPE_ARRAY_1D, DTYPE_ARRAY_2D)
    
    def create_widget(self, var_name: str, color: QColor, 
                      parent: Optional[QWidget] = None) -> QWidget:
        return WaveformWidget(var_name, color, parent)
    
    def update(self, widget: QWidget, value: Any, dtype: str,
               shape: Optional[Tuple[int, ...]] = None,
               source_info: str = "") -> None:
        if isinstance(widget, WaveformWidget):
            widget.update_data(value, dtype, shape, source_info)
```

### `pyprobe/plugins/builtins/constellation.py`
```python
"""Constellation diagram plugin for complex arrays."""
from typing import Any, Optional, Tuple
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QColor

from ..base import ProbePlugin
from ...core.data_classifier import DTYPE_ARRAY_COMPLEX


class ConstellationWidget(QWidget):
    """Scatter plot widget for I/Q data."""
    # Copy implementation from existing constellation.py
    # Modify to use provided color parameter
    pass


class ConstellationPlugin(ProbePlugin):
    """Plugin for visualizing complex arrays as constellation diagrams."""
    
    name = "Constellation"
    icon = "constellation"
    priority = 100  # High priority for complex arrays
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype == DTYPE_ARRAY_COMPLEX
    
    def create_widget(self, var_name: str, color: QColor,
                      parent: Optional[QWidget] = None) -> QWidget:
        return ConstellationWidget(var_name, color, parent)
    
    def update(self, widget: QWidget, value: Any, dtype: str,
               shape: Optional[Tuple[int, ...]] = None,
               source_info: str = "") -> None:
        if isinstance(widget, ConstellationWidget):
            widget.update_data(value, dtype, shape, source_info)
```

### `pyprobe/plugins/builtins/scalar_history.py`
```python
"""Scalar history chart plugin - shows value over time."""
from typing import Any, Optional, Tuple
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QColor

from ..base import ProbePlugin
from ...core.data_classifier import DTYPE_SCALAR


class ScalarHistoryWidget(QWidget):
    """Chart showing scalar values over multiple frames."""
    # Copy implementation from existing scalar_history_chart.py
    pass


class ScalarHistoryPlugin(ProbePlugin):
    """Plugin for visualizing scalar values as a time-series chart."""
    
    name = "History"
    icon = "chart"
    priority = 100  # High priority for scalars
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype == DTYPE_SCALAR
    
    def create_widget(self, var_name: str, color: QColor,
                      parent: Optional[QWidget] = None) -> QWidget:
        return ScalarHistoryWidget(var_name, color, parent)
    
    def update(self, widget: QWidget, value: Any, dtype: str,
               shape: Optional[Tuple[int, ...]] = None,
               source_info: str = "") -> None:
        if isinstance(widget, ScalarHistoryWidget):
            widget.update_data(value, dtype, shape, source_info)
```

### `pyprobe/plugins/builtins/scalar_display.py`
```python
"""Simple scalar display plugin - shows current value only."""
from typing import Any, Optional, Tuple
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QColor

from ..base import ProbePlugin
from ...core.data_classifier import DTYPE_SCALAR


class ScalarDisplayWidget(QWidget):
    """Simple numeric display for scalar values."""
    # Copy implementation from existing scalar_display.py
    pass


class ScalarDisplayPlugin(ProbePlugin):
    """Plugin for displaying scalar values as simple text."""
    
    name = "Value"
    icon = "number"
    priority = 50  # Lower priority than History for scalars
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype == DTYPE_SCALAR
    
    def create_widget(self, var_name: str, color: QColor,
                      parent: Optional[QWidget] = None) -> QWidget:
        return ScalarDisplayWidget(var_name, color, parent)
    
    def update(self, widget: QWidget, value: Any, dtype: str,
               shape: Optional[Tuple[int, ...]] = None,
               source_info: str = "") -> None:
        if isinstance(widget, ScalarDisplayWidget):
            widget.update_data(value, dtype, shape, source_info)
```

---

## New Plugins to Add (M2 scope)

### `pyprobe/plugins/builtins/spectrum.py`
```python
"""FFT spectrum plugin - show frequency content of 1D arrays."""
from typing import Any, Optional, Tuple
import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QColor

from ..base import ProbePlugin
from ...core.data_classifier import DTYPE_ARRAY_1D, DTYPE_ARRAY_COMPLEX


class SpectrumWidget(QWidget):
    """FFT magnitude plot."""
    # New implementation for frequency domain view
    pass


class SpectrumPlugin(ProbePlugin):
    """Plugin for visualizing frequency content via FFT."""
    
    name = "Spectrum"
    icon = "spectrum"
    priority = 50  # Secondary option for arrays
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype in (DTYPE_ARRAY_1D, DTYPE_ARRAY_COMPLEX)
    
    # ... implementation
```

### `pyprobe/plugins/builtins/iq_split.py`
```python
"""I/Q split view plugin - show real and imaginary as separate waveforms."""
from typing import Any, Optional, Tuple
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QColor

from ..base import ProbePlugin
from ...core.data_classifier import DTYPE_ARRAY_COMPLEX


class IQSplitWidget(QWidget):
    """Dual waveform plot for I and Q channels."""
    pass


class IQSplitPlugin(ProbePlugin):
    """Plugin for visualizing complex arrays as separate I/Q waveforms."""
    
    name = "I/Q Split"
    icon = "iq"
    priority = 50  # Secondary option for complex
    
    def can_handle(self, dtype: str, shape: Optional[Tuple[int, ...]]) -> bool:
        return dtype == DTYPE_ARRAY_COMPLEX
    
    # ... implementation
```

---

## Files to Deprecate (not delete immediately)

Mark as deprecated with docstring warning:
- `pyprobe/plots/base_plot.py` → "Deprecated: Use pyprobe.plugins.base.ProbePlugin"
- `pyprobe/plots/plot_factory.py` → "Deprecated: Use pyprobe.plugins.PluginRegistry"

---

## Verification

```bash
# Test plugin discovery
python -c "
from pyprobe.plugins import PluginRegistry
from pyprobe.core.data_classifier import DTYPE_ARRAY_1D, DTYPE_ARRAY_COMPLEX, DTYPE_SCALAR

reg = PluginRegistry.instance()

# Test dtype matching
print('1D array plugins:', [p.name for p in reg.get_compatible_plugins(DTYPE_ARRAY_1D)])
print('Complex plugins:', [p.name for p in reg.get_compatible_plugins(DTYPE_ARRAY_COMPLEX)])
print('Scalar plugins:', [p.name for p in reg.get_compatible_plugins(DTYPE_SCALAR)])

# Test default selection
print('Default for 1D:', reg.get_default_plugin(DTYPE_ARRAY_1D).name)
print('Default for complex:', reg.get_default_plugin(DTYPE_ARRAY_COMPLEX).name)
print('Default for scalar:', reg.get_default_plugin(DTYPE_SCALAR).name)
"
# Expected:
# 1D array plugins: ['Waveform', 'Spectrum']
# Complex plugins: ['Constellation', 'I/Q Split', 'Spectrum']
# Scalar plugins: ['History', 'Value']
# Default for 1D: Waveform
# Default for complex: Constellation
# Default for scalar: History
```

---

## Merge Conflict Risk

**Low** - Only creates new files in `pyprobe/plugins/builtins/`.
