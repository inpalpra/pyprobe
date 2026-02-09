from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.capture_manager import CaptureManager
from pyprobe.core.sequence import SequenceGenerator


def _anchor(symbol: str) -> ProbeAnchor:
    return ProbeAnchor(
        file="/tmp/example.py",
        line=1,
        col=0,
        symbol=symbol,
        func="",
        is_assignment=False,
    )


def test_capture_immediate_sequence_increments() -> None:
    seq_gen = SequenceGenerator()
    manager = CaptureManager(seq_gen=seq_gen, clock=lambda: 100)

    record_a = manager.capture_immediate(
        anchor=_anchor("a"),
        value=1,
        dtype="scalar",
        shape=None,
    )
    record_b = manager.capture_immediate(
        anchor=_anchor("b"),
        value=2,
        dtype="scalar",
        shape=None,
    )

    assert record_a.seq_num == 0
    assert record_b.seq_num == 1
    assert record_a.timestamp == 100
    assert record_b.timestamp == 100


def test_capture_batch_timestamp_and_logical_order() -> None:
    manager = CaptureManager(seq_gen=SequenceGenerator())

    items = [
        (_anchor("x"), 1, "scalar", None),
        (_anchor("y"), 2, "scalar", None),
        (_anchor("z"), 3, "scalar", None),
    ]

    records = manager.capture_batch(items, timestamp=123)

    assert [r.logical_order for r in records] == [0, 1, 2]
    assert [r.seq_num for r in records] == [0, 1, 2]
    assert all(r.timestamp == 123 for r in records)


def test_defer_capture_reserves_sequence() -> None:
    seq_gen = SequenceGenerator()
    manager = CaptureManager(seq_gen=seq_gen, clock=lambda: 111)

    manager.defer_capture(frame_id=1, anchor=_anchor("x"), logical_order=0)
    immediate = manager.capture_immediate(
        anchor=_anchor("y"),
        value=2,
        dtype="scalar",
        shape=None,
    )

    def resolver(anchor: ProbeAnchor):
        return (10, "scalar", None)

    records = manager.flush_deferred(frame_id=1, event="line", resolve_value=resolver)

    assert len(records) == 1
    assert records[0].seq_num == 0
    assert immediate.seq_num == 1
    assert records[0].timestamp == 111


def test_flush_deferred_on_return_and_exception() -> None:
    manager = CaptureManager(seq_gen=SequenceGenerator(), clock=lambda: 222)
    anchor = _anchor("x")
    manager.defer_capture(frame_id=2, anchor=anchor)

    def resolver(a: ProbeAnchor):
        return (5, "scalar", None)

    records_return = manager.flush_deferred(
        frame_id=2,
        event="return",
        resolve_value=resolver,
    )
    assert len(records_return) == 1

    manager.defer_capture(frame_id=3, anchor=anchor)
    records_exception = manager.flush_deferred(
        frame_id=3,
        event="exception",
        resolve_value=resolver,
    )
    assert len(records_exception) == 1
