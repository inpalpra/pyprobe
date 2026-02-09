import os
from typing import List

import pytest

from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.tracer import VariableTracer


def _line_number(lines: List[str], needle: str) -> int:
    for idx, line in enumerate(lines, start=1):
        if line.strip() == needle:
            return idx
    raise AssertionError(f"Line not found: {needle}")


def _run_tracer(source: str, anchors: List[ProbeAnchor]):
    records = []

    def on_batch(batch):
        records.extend(batch)

    tracer = VariableTracer(
        data_callback=lambda _: None,
        target_files=None,
        capture_record_batch_callback=on_batch,
    )

    for anchor in anchors:
        tracer.add_anchor_watch(anchor)

    tracer.start_anchored()
    try:
        exec(compile(source, "<test>", "exec"), {})
    finally:
        tracer.stop()

    return records


def test_loop_ordering_lhs_capture():
    source = "\n".join(
        [
            "def main():",
            "    x = 10",
            "    for i in range(3):",
            "        x = x - 1",
            "    return x",
            "",
            "main()",
        ]
    )
    lines = source.splitlines()
    assign_line = _line_number(lines, "x = x - 1")

    anchor = ProbeAnchor(
        file="<test>",
        line=assign_line,
        col=8,
        symbol="x",
        func="main",
        is_assignment=True,
    )

    records = _run_tracer(source, [anchor])
    values = [r.value for r in records]

    assert values == [9, 8, 7]
    assert [r.seq_num for r in records] == sorted(r.seq_num for r in records)


def test_multi_probe_same_line_ordering():
    source = "\n".join(
        [
            "def main():",
            "    a = 1",
            "    b = 2",
            "    x = a + b",
            "    return x",
            "",
            "main()",
        ]
    )
    lines = source.splitlines()
    line_no = _line_number(lines, "x = a + b")

    anchor_a = ProbeAnchor(
        file="<test>",
        line=line_no,
        col=8,
        symbol="a",
        func="main",
        is_assignment=False,
    )
    anchor_b = ProbeAnchor(
        file="<test>",
        line=line_no,
        col=12,
        symbol="b",
        func="main",
        is_assignment=False,
    )
    anchor_x = ProbeAnchor(
        file="<test>",
        line=line_no,
        col=4,
        symbol="x",
        func="main",
        is_assignment=True,
    )

    records = _run_tracer(source, [anchor_a, anchor_b, anchor_x])
    records.sort(key=lambda r: r.seq_num)

    assert [r.value for r in records] == [1, 2, 3]
    assert [r.logical_order for r in records] == [0, 1, 2]


def test_function_return_flushes_deferred():
    source = "\n".join(
        [
            "def foo():",
            "    x = 42",
            "    return",
            "",
            "foo()",
        ]
    )
    lines = source.splitlines()
    line_no = _line_number(lines, "x = 42")

    anchor = ProbeAnchor(
        file="<test>",
        line=line_no,
        col=4,
        symbol="x",
        func="foo",
        is_assignment=True,
    )

    records = _run_tracer(source, [anchor])

    assert len(records) == 1
    assert records[0].value == 42


@pytest.mark.skipif(
    os.environ.get("PYPROBE_STRESS") is None,
    reason="Set PYPROBE_STRESS=1 to run the 1M-iteration stress test.",
)
def test_high_frequency_loop_capture():
    iterations = 1_000_000
    source = "\n".join(
        [
            "def main():",
            f"    for i in range({iterations}):",
            "        x = i",
            "    return",
            "",
            "main()",
        ]
    )
    lines = source.splitlines()
    line_no = _line_number(lines, "x = i")

    anchor = ProbeAnchor(
        file="<test>",
        line=line_no,
        col=8,
        symbol="x",
        func="main",
        is_assignment=True,
    )

    records = _run_tracer(source, [anchor])

    assert len(records) == iterations
    assert records[0].value == 0
    assert records[-1].value == iterations - 1
