"""Unit tests for AxisController."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication
import sys

from pyprobe.plots.axis_controller import AxisController, AxisPinState


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def plot_item(app):
    return pg.PlotItem()


@pytest.fixture
def controller(plot_item):
    return AxisController(plot_item)


class TestAxisControllerInitialState:
    def test_x_starts_unpinned(self, controller):
        assert not controller.x_pinned

    def test_y_starts_unpinned(self, controller):
        assert not controller.y_pinned

    def test_is_pinned_x(self, controller):
        assert not controller.is_pinned('x')

    def test_is_pinned_y(self, controller):
        assert not controller.is_pinned('y')

    def test_invalid_axis_raises(self, controller):
        with pytest.raises(ValueError):
            controller.is_pinned('z')


class TestAxisControllerSetPinned:
    def test_pin_x(self, controller):
        controller.set_pinned('x', True)
        assert controller.x_pinned

    def test_pin_y(self, controller):
        controller.set_pinned('y', True)
        assert controller.y_pinned

    def test_unpin_x(self, controller):
        controller.set_pinned('x', True)
        controller.set_pinned('x', False)
        assert not controller.x_pinned

    def test_unpin_y(self, controller):
        controller.set_pinned('y', True)
        controller.set_pinned('y', False)
        assert not controller.y_pinned


class TestAxisControllerToggle:
    def test_toggle_pins(self, controller):
        controller.toggle_pin('x')
        assert controller.x_pinned

    def test_toggle_twice_unpins(self, controller):
        controller.toggle_pin('x')
        controller.toggle_pin('x')
        assert not controller.x_pinned


class TestAxisControllerReset:
    def test_reset_unpins_both(self, controller):
        controller.set_pinned('x', True)
        controller.set_pinned('y', True)
        controller.reset()
        assert not controller.x_pinned
        assert not controller.y_pinned


class TestAxisControllerSignals:
    def test_signal_emitted_on_pin(self, controller):
        received = []
        controller.pin_state_changed.connect(lambda axis, pinned: received.append((axis, pinned)))
        controller.set_pinned('x', True)
        assert ('x', True) in received

    def test_no_signal_when_unchanged(self, controller):
        received = []
        controller.pin_state_changed.connect(lambda axis, pinned: received.append((axis, pinned)))
        # x is already unpinned, setting to unpinned should not emit
        controller.set_pinned('x', False)
        assert len(received) == 0
