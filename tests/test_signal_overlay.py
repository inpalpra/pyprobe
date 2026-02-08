"""Unit tests for signal overlay drag-and-drop helpers."""

import pytest
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QMimeData
from PyQt6.QtGui import QColor

from pyprobe.gui.drag_helpers import encode_anchor_mime, decode_anchor_mime, has_anchor_mime, MIME_TYPE


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


class TestMimeEncoding:
    def test_encode_creates_mime(self, app):
        mime = encode_anchor_mime("/path/test.py", 42, 8, "signal_x", "process")
        assert mime.hasFormat(MIME_TYPE)

    def test_roundtrip(self, app):
        mime = encode_anchor_mime("/path/test.py", 42, 8, "signal_x", "process")
        data = decode_anchor_mime(mime)
        assert data is not None
        assert data['file'] == "/path/test.py"
        assert data['line'] == 42
        assert data['col'] == 8
        assert data['symbol'] == "signal_x"
        assert data['func'] == "process"

    def test_has_anchor_mime_true(self, app):
        mime = encode_anchor_mime("/path/test.py", 1, 0, "x")
        assert has_anchor_mime(mime)

    def test_has_anchor_mime_false(self, app):
        mime = QMimeData()
        assert not has_anchor_mime(mime)

    def test_decode_invalid_returns_none(self, app):
        mime = QMimeData()
        mime.setData(MIME_TYPE, b"not json")
        result = decode_anchor_mime(mime)
        assert result is None

    def test_decode_no_format_returns_none(self, app):
        mime = QMimeData()
        result = decode_anchor_mime(mime)
        assert result is None
