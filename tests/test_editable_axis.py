"""Unit tests for EditableAxisItem wheel behavior."""

import sys

import pyqtgraph as pg
import pytest
from PyQt6.QtWidgets import QApplication

from pyprobe.plots.editable_axis import EditableAxisItem


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


class _DummyView:
    def __init__(self, wheel_scale: float):
        self.state = {
            'wheelScaleFactor': wheel_scale,
            'mouseEnabled': [False, False],
        }


@pytest.mark.parametrize("orientation", ["left", "right"])
def test_vertical_axis_wheel_inverts_zoom_direction(monkeypatch, app, orientation):
    axis = EditableAxisItem(orientation)
    view = _DummyView(wheel_scale=1.5)
    captured_scales = []

    monkeypatch.setattr(EditableAxisItem, 'linkedView', lambda self: view)

    def _fake_super_wheel(self, event):
        captured_scales.append(self.linkedView().state['wheelScaleFactor'])

    monkeypatch.setattr(pg.AxisItem, 'wheelEvent', _fake_super_wheel)

    axis.wheelEvent(object())

    assert captured_scales == [-1.5]
    assert view.state['wheelScaleFactor'] == 1.5
    assert view.state['mouseEnabled'] == [False, False]


@pytest.mark.parametrize("orientation", ["bottom", "top"])
def test_horizontal_axis_wheel_keeps_zoom_direction(monkeypatch, app, orientation):
    axis = EditableAxisItem(orientation)
    view = _DummyView(wheel_scale=1.5)
    captured_scales = []

    monkeypatch.setattr(EditableAxisItem, 'linkedView', lambda self: view)

    def _fake_super_wheel(self, event):
        captured_scales.append(self.linkedView().state['wheelScaleFactor'])

    monkeypatch.setattr(pg.AxisItem, 'wheelEvent', _fake_super_wheel)

    axis.wheelEvent(object())

    assert captured_scales == [1.5]
    assert view.state['wheelScaleFactor'] == 1.5
    assert view.state['mouseEnabled'] == [False, False]
