import logging

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.capture_record import CaptureRecord
from pyprobe.gui.probe_buffer import ProbeDataBuffer


def _anchor() -> ProbeAnchor:
    return ProbeAnchor(
        file="/tmp/example.py",
        line=1,
        col=0,
        symbol="x",
        func="",
        is_assignment=False,
    )


def _record(seq: int, value: int) -> CaptureRecord:
    return CaptureRecord(
        anchor=_anchor(),
        value=value,
        dtype="scalar",
        shape=None,
        seq_num=seq,
        timestamp=100 + seq,
        logical_order=0,
    )


def test_probe_buffer_appends_and_returns_plot_data() -> None:
    buffer = ProbeDataBuffer(anchor=_anchor())

    buffer.append(_record(0, 10))
    buffer.append(_record(1, 20))

    timestamps, values = buffer.get_plot_data()

    assert buffer.count == 2
    assert buffer.last_seq == 1
    assert timestamps == [100, 101]
    assert values == [10, 20]


def test_probe_buffer_logs_out_of_order(caplog) -> None:
    buffer = ProbeDataBuffer(anchor=_anchor())

    buffer.append(_record(5, 10))

    caplog.set_level(logging.WARNING)
    buffer.append(_record(4, 20))

    assert "Out of order capture" in caplog.text
