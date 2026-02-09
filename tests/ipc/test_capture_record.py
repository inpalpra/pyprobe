from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.capture_record import CaptureRecord


def test_capture_record_serialization_roundtrip() -> None:
    anchor = ProbeAnchor(
        file="/tmp/example.py",
        line=10,
        col=2,
        symbol="value",
        func="main",
        is_assignment=False,
    )

    record = CaptureRecord(
        anchor=anchor,
        value=123,
        dtype="scalar",
        shape=None,
        seq_num=5,
        timestamp=42,
        logical_order=1,
    )

    payload = record.to_dict()
    restored = CaptureRecord.from_dict(payload)

    assert restored.anchor == record.anchor
    assert restored.value == record.value
    assert restored.dtype == record.dtype
    assert restored.shape == record.shape
    assert restored.seq_num == record.seq_num
    assert restored.timestamp == record.timestamp
    assert restored.logical_order == record.logical_order
