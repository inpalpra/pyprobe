"""Unit tests for PlotToolbar."""

import pytest
import sys
from PyQt6.QtWidgets import QApplication

from pyprobe.gui.plot_toolbar import PlotToolbar, InteractionMode


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def toolbar(app):
    return PlotToolbar()


class TestPlotToolbarDefaults:
    def test_default_mode_is_pointer(self, toolbar):
        assert toolbar.current_mode == InteractionMode.POINTER


class TestPlotToolbarModeChange:
    def test_mode_changed_signal(self, toolbar):
        received = []
        toolbar.mode_changed.connect(received.append)
        toolbar._on_mode_clicked(InteractionMode.ZOOM)
        assert InteractionMode.ZOOM in received

    def test_set_mode(self, toolbar):
        toolbar.set_mode(InteractionMode.PAN)
        assert toolbar.current_mode == InteractionMode.PAN


class TestPlotToolbarReset:
    def test_reset_signal(self, toolbar):
        called = []
        toolbar.reset_requested.connect(lambda: called.append(True))
        toolbar._reset_btn.click()
        assert len(called) == 1


class TestPlotToolbarRevert:
    def test_revert_to_pointer(self, toolbar):
        toolbar.set_mode(InteractionMode.ZOOM)
        toolbar.revert_to_pointer()
        assert toolbar.current_mode == InteractionMode.POINTER
