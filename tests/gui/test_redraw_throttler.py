from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.capture_record import CaptureRecord
from pyprobe.gui.redraw_throttler import RedrawThrottler


def _anchor() -> ProbeAnchor:
    return ProbeAnchor(
        file="/tmp/example.py",
        line=1,
        col=0,
        symbol="x",
        func="",
        is_assignment=False,
    )


def _record(seq: int) -> CaptureRecord:
    return CaptureRecord(
        anchor=_anchor(),
        value=seq,
        dtype="scalar",
        shape=None,
        seq_num=seq,
        timestamp=100 + seq,
        logical_order=0,
    )


def test_redraw_throttler_marks_dirty_and_returns_buffers() -> None:
    throttler = RedrawThrottler()

    throttler.receive(_record(0))
    throttler.receive(_record(1))

    dirty = throttler.get_dirty_buffers()

    assert list(dirty.keys()) == [_anchor()]
    assert throttler.buffer_count == 1
    assert throttler.buffer_for(_anchor()) is not None

    dirty_again = throttler.get_dirty_buffers()
    assert dirty_again == {}


def test_redraw_throttler_limits_redraw_rate() -> None:
    current = [0.0]

    def clock():
        return current[0]

    throttler = RedrawThrottler(min_interval_ms=10.0, clock=clock)

    assert throttler.should_redraw() is False

    current[0] = 0.01
    assert throttler.should_redraw() is True

    current[0] = 0.015
    assert throttler.should_redraw() is False

    current[0] = 0.021
    assert throttler.should_redraw() is True
