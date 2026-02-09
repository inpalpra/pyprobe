"""
Drag-and-drop helpers for signal overlay.
Provides MIME encoding/decoding for probe anchors.
"""

import json
from typing import Optional
from PyQt6.QtCore import QMimeData

from pyprobe.logging import get_logger
logger = get_logger(__name__)

MIME_TYPE = 'application/x-pyprobe-anchor'


def encode_anchor_mime(file: str, line: int, col: int, symbol: str, func: str = "", is_assignment: bool = False) -> QMimeData:
    """Encode probe anchor data into QMimeData for drag-and-drop.
    
    Args:
        file: Source file path
        line: Line number
        col: Column number
        symbol: Variable name
        func: Enclosing function name
        is_assignment: True if this is an assignment target (LHS)
    
    Returns:
        QMimeData with encoded anchor
    """
    data = {
        'file': file,
        'line': line,
        'col': col,
        'symbol': symbol,
        'func': func,
        'is_assignment': is_assignment,
    }
    mime_data = QMimeData()
    mime_data.setData(MIME_TYPE, json.dumps(data).encode('utf-8'))
    logger.debug(f"Encoded anchor MIME: {symbol} at {file}:{line}")
    return mime_data


def decode_anchor_mime(mime_data: QMimeData) -> Optional[dict]:
    """Decode probe anchor data from QMimeData.
    
    Args:
        mime_data: The MIME data from a drop event
    
    Returns:
        Dict with anchor data, or None if invalid
    """
    if not mime_data.hasFormat(MIME_TYPE):
        return None
    
    try:
        raw = bytes(mime_data.data(MIME_TYPE)).decode('utf-8')
        data = json.loads(raw)
        logger.debug(f"Decoded anchor MIME: {data.get('symbol')} at {data.get('file')}:{data.get('line')}")
        return data
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.debug(f"Failed to decode anchor MIME: {e}")
        return None


def has_anchor_mime(mime_data: QMimeData) -> bool:
    """Check if mime data contains anchor data."""
    return mime_data.hasFormat(MIME_TYPE)
