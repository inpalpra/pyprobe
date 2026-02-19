"""Phase 3.3: Pin indicator positioning tests.

Verifies pin buttons are inside the plot area, respond to resize,
and click toggles axis state.
"""

import pytest
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor

from pyprobe.plots.pin_indicator import PinIndicator, PinButton


@pytest.fixture
def indicator(qapp):
    """Create a PinIndicator."""
    pi = PinIndicator()
    pi.resize(600, 400)
    pi.show()
    qapp.processEvents()
    return pi


class TestPinButtonState:
    def test_initial_unpinned(self, indicator):
        """Buttons start unpinned."""
        assert not indicator._x_btn.is_pinned
        assert not indicator._y_btn.is_pinned

    def test_set_x_pinned(self, indicator):
        """set_x_pinned updates button state."""
        indicator.set_x_pinned(True)
        assert indicator._x_btn.is_pinned
        assert indicator._x_btn.isChecked()

    def test_set_y_pinned(self, indicator):
        """set_y_pinned updates button state."""
        indicator.set_y_pinned(True)
        assert indicator._y_btn.is_pinned
        assert indicator._y_btn.isChecked()

    def test_update_state(self, indicator):
        """update_state dispatches to correct button."""
        indicator.update_state('x', True)
        assert indicator._x_btn.is_pinned
        indicator.update_state('y', True)
        assert indicator._y_btn.is_pinned


class TestPinButtonOpacity:
    def test_unpinned_opacity_low(self, indicator):
        """Unpinned buttons have low opacity."""
        assert indicator._x_btn._opacity_effect.opacity() < 0.5

    def test_pinned_opacity_high(self, indicator):
        """Pinned buttons have full opacity."""
        indicator.set_x_pinned(True)
        assert indicator._x_btn._opacity_effect.opacity() == 1.0


class TestPinIndicatorLayout:
    def test_buttons_inside_view_rect(self, indicator, qapp):
        """After update_layout, buttons are within the view rect."""
        view_rect = QRectF(50, 30, 500, 340)
        indicator.update_layout(view_rect)
        qapp.processEvents()

        # Y button should be near top-left of view rect
        y_pos = indicator._y_btn.pos()
        assert y_pos.x() >= view_rect.left()
        assert y_pos.y() >= view_rect.top()

        # X button should be near bottom of view rect
        x_pos = indicator._x_btn.pos()
        assert x_pos.y() >= view_rect.top()  # within vertical bounds

    def test_layout_responds_to_different_rect(self, indicator, qapp):
        """Changing view rect moves the buttons."""
        rect1 = QRectF(10, 10, 300, 200)
        indicator.update_layout(rect1)
        qapp.processEvents()
        pos1_x = indicator._x_btn.pos().x()

        rect2 = QRectF(10, 10, 500, 200)
        indicator.update_layout(rect2)
        qapp.processEvents()
        pos2_x = indicator._x_btn.pos().x()

        # X button should move when rect width changes
        assert pos1_x != pos2_x


class TestPinButtonSignals:
    def test_x_click_emits_signal(self, indicator, qapp):
        """Clicking X button emits x_pin_clicked."""
        received = []
        indicator.x_pin_clicked.connect(lambda: received.append('x'))
        indicator._x_btn.click()
        qapp.processEvents()
        assert 'x' in received

    def test_y_click_emits_signal(self, indicator, qapp):
        """Clicking Y button emits y_pin_clicked."""
        received = []
        indicator.y_pin_clicked.connect(lambda: received.append('y'))
        indicator._y_btn.click()
        qapp.processEvents()
        assert 'y' in received


class TestPinIndicatorWithToolbarRect:
    def test_set_toolbar_rect_used(self, indicator, qapp):
        """set_toolbar_rect adjusts X button position if method exists."""
        if not hasattr(indicator, 'set_toolbar_rect'):
            pytest.skip("set_toolbar_rect not yet implemented (Phase 4)")

        from PyQt6.QtCore import QRect
        toolbar_rect = QRect(450, 350, 130, 40)
        indicator.set_toolbar_rect(toolbar_rect)

        view_rect = QRectF(10, 10, 580, 380)
        indicator.update_layout(view_rect)
        qapp.processEvents()

        # X button should be to the left of the toolbar
        x_pos = indicator._x_btn.pos()
        assert x_pos.x() < toolbar_rect.left()
