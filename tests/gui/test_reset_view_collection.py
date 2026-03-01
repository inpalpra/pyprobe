"""
Reproduction script for reset_view crash with waveform collection data.

This test verifies that reset_view() works when self._data is a list
(waveform/array collection), not just a numpy array.

Run with:
    .venv/bin/python -m pytest tests/gui/test_reset_view_collection.py -v
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtGui import QColor


class TestResetViewWithCollectionData:
    """Verify reset_view handles list-type _data (waveform/array collections)."""

    @pytest.fixture
    def waveform_widget(self, qapp):
        """Create a WaveformWidget with minimal setup."""
        from pyprobe.plugins.builtins.waveform import WaveformWidget
        widget = WaveformWidget("test", QColor("#00ff00"))
        widget.show()
        qapp.processEvents()
        yield widget
        widget.close()


    def test_reset_view_with_waveform_collection(self, waveform_widget, qapp):
        """reset_view() should not crash when _data is a list of waveform dicts."""
        from pyprobe.core.data_classifier import DTYPE_WAVEFORM_COLLECTION

        # Simulate what _update_waveform_collection_data stores
        collection = {
            '__dtype__': DTYPE_WAVEFORM_COLLECTION,
            'waveforms': [
                {'samples': np.sin(np.linspace(0, 2*np.pi, 100)), 'scalars': [0.0, 0.01]},
                {'samples': np.cos(np.linspace(0, 2*np.pi, 100)), 'scalars': [0.0, 0.01]},
            ]
        }

        # Feed the collection through the normal update path
        waveform_widget.update_data(collection, DTYPE_WAVEFORM_COLLECTION, (2,), "test")
        qapp.processEvents()

        # This should NOT raise AttributeError: 'list' object has no attribute 'ndim'
        waveform_widget.reset_view()
        qapp.processEvents()

    def test_reset_view_with_array_collection(self, waveform_widget, qapp):
        """reset_view() should not crash when _data is a list of numpy arrays."""
        from pyprobe.core.data_classifier import DTYPE_ARRAY_COLLECTION

        collection = {
            '__dtype__': DTYPE_ARRAY_COLLECTION,
            'arrays': [
                np.random.randn(100),
                np.random.randn(100),
            ]
        }

        waveform_widget.update_data(collection, DTYPE_ARRAY_COLLECTION, (2,), "test")
        qapp.processEvents()

        # This should NOT raise AttributeError: 'list' object has no attribute 'ndim'
        waveform_widget.reset_view()
        qapp.processEvents()
