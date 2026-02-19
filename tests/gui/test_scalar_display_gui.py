"""Phase 2.4: Scalar display visual correctness tests.

Verifies value label text, complex formatting, and initial state.
"""

import pytest
from PyQt6.QtGui import QColor

from pyprobe.plugins.builtins.scalar_display import ScalarDisplayWidget, ScalarDisplayPlugin
from pyprobe.core.data_classifier import DTYPE_SCALAR


@pytest.fixture
def scalar_display(qapp, probe_color):
    """Create a ScalarDisplayWidget for testing."""
    w = ScalarDisplayWidget("my_value", probe_color)
    w.resize(300, 200)
    w.show()
    qapp.processEvents()
    return w


class TestScalarDisplayValues:
    def test_integer_display(self, scalar_display):
        """Integer value displayed correctly."""
        scalar_display.update_data(42, DTYPE_SCALAR)
        assert "42" in scalar_display._value_label.text()

    def test_float_display(self, scalar_display):
        """Float value displayed correctly."""
        scalar_display.update_data(3.14159, DTYPE_SCALAR)
        text = scalar_display._value_label.text()
        assert "3.14" in text

    def test_complex_display(self, scalar_display):
        """Complex number formatted as a + bj."""
        scalar_display.update_data(3+4j, DTYPE_SCALAR)
        text = scalar_display._value_label.text()
        assert "3" in text
        assert "4" in text
        assert "j" in text

    def test_complex_negative_imag(self, scalar_display):
        """Complex number with negative imaginary part uses minus sign."""
        scalar_display.update_data(1-2j, DTYPE_SCALAR)
        text = scalar_display._value_label.text()
        assert "-" in text
        assert "2" in text

    def test_none_display(self, scalar_display):
        """None value shows dash."""
        scalar_display.update_data(None, DTYPE_SCALAR)
        assert "--" in scalar_display._value_label.text()


class TestScalarDisplayLabels:
    def test_name_label(self, scalar_display):
        """Name label matches variable name."""
        assert scalar_display._name_label.text() == "my_value"

    def test_initial_placeholder(self, scalar_display):
        """Before any data, shows placeholder text."""
        assert "Nothing to show" in scalar_display._value_label.text()

    def test_info_label_after_update(self, scalar_display):
        """Info label shows type information."""
        scalar_display.update_data(42, DTYPE_SCALAR)
        text = scalar_display._info_label.text()
        assert "int" in text


class TestScalarDisplayPlugin:
    def test_can_handle_scalar(self):
        assert ScalarDisplayPlugin().can_handle(DTYPE_SCALAR, None)

    def test_cannot_handle_array(self):
        assert not ScalarDisplayPlugin().can_handle('array_1d', None)

    def test_priority_lower_than_history(self):
        """Value plugin has lower priority than History (so History is default)."""
        from pyprobe.plugins.builtins.scalar_history import ScalarHistoryPlugin
        assert ScalarDisplayPlugin().priority < ScalarHistoryPlugin().priority

    def test_create_widget(self, qapp, probe_color):
        w = ScalarDisplayPlugin().create_widget("x", probe_color)
        assert isinstance(w, ScalarDisplayWidget)
