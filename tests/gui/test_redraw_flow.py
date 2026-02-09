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


class _FakePanel:
    def __init__(self):
        self.history = None

    def update_from_buffer(self, buffer):
        self.history = buffer.get_plot_data()


def test_record_buffer_redraw_flow() -> None:
    current = [0.0]

    def clock():
        return current[0]

    throttler = RedrawThrottler(min_interval_ms=1.0, clock=clock)

    throttler.receive(_record(0, 10))
    throttler.receive(_record(1, 20))

    current[0] = 0.002
    assert throttler.should_redraw() is True

    dirty = throttler.get_dirty_buffers()
    assert list(dirty.keys()) == [_anchor()]

    panel = _FakePanel()
    for buffer in dirty.values():
        panel.update_from_buffer(buffer)

    timestamps, values = panel.history
    assert timestamps == [100, 101]
    assert values == [10, 20]
