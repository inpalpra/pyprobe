from pyprobe.core.anchor import ProbeAnchor
from pyprobe.ipc.messages import make_probe_value_batch_msg, make_probe_value_msg, MessageType


def test_probe_value_message_includes_sequence_fields() -> None:
    anchor = ProbeAnchor(
        file="/tmp/example.py",
        line=3,
        col=0,
        symbol="x",
        func="",
        is_assignment=False,
    )

    msg = make_probe_value_msg(
        anchor=anchor,
        value=1,
        dtype="scalar",
        shape=None,
        seq_num=7,
        timestamp=123456,
        logical_order=0,
    )

    assert msg.msg_type == MessageType.DATA_PROBE_VALUE
    assert msg.payload["seq_num"] == 7
    assert msg.payload["timestamp"] == 123456
    assert msg.payload["logical_order"] == 0


def test_probe_value_batch_message_includes_sequence_fields() -> None:
    anchor = ProbeAnchor(
        file="/tmp/example.py",
        line=3,
        col=0,
        symbol="x",
        func="",
        is_assignment=False,
    )

    probes = [
        (anchor, 1, "scalar", None, 10, 987, 0),
        (anchor, 2, "scalar", None, 11, 987, 1),
    ]

    msg = make_probe_value_batch_msg(probes)

    assert msg.msg_type == MessageType.DATA_PROBE_VALUE_BATCH
    assert len(msg.payload["probes"]) == 2
    assert msg.payload["probes"][0]["seq_num"] == 10
    assert msg.payload["probes"][0]["timestamp"] == 987
    assert msg.payload["probes"][0]["logical_order"] == 0
    assert msg.payload["probes"][1]["seq_num"] == 11
    assert msg.payload["probes"][1]["logical_order"] == 1
