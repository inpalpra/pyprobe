from pyprobe.core.anchor import ProbeAnchor
from pyprobe.core.tracer import VariableTracer


def _line_number(lines: list[str], needle: str) -> int:
    for idx, line in enumerate(lines, start=1):
        if line.strip() == needle:
            return idx
    raise AssertionError(f"Line not found: {needle}")


def test_tracer_emits_capture_records_for_rhs_and_lhs(tmp_path) -> None:
    source = "\n".join(
        [
            "def main():",
            "    x = 1",
            "    y = x + 1",
            "    x = y",
            "    return",
            "",
            "main()",
        ]
    )
    path = tmp_path / "sample.py"
    path.write_text(source)

    lines = source.splitlines()
    rhs_line = _line_number(lines, "y = x + 1")
    lhs_line = _line_number(lines, "x = y")

    rhs_anchor = ProbeAnchor(
        file=str(path),
        line=rhs_line,
        col=0,
        symbol="x",
        func="main",
        is_assignment=False,
    )
    lhs_anchor = ProbeAnchor(
        file=str(path),
        line=lhs_line,
        col=0,
        symbol="x",
        func="main",
        is_assignment=True,
    )

    records = []

    def on_batch(batch):
        records.extend(batch)

    tracer = VariableTracer(
        data_callback=lambda _: None,
        target_files={str(path)},
        capture_record_batch_callback=on_batch,
    )
    tracer.add_anchor_watch(rhs_anchor)
    tracer.add_anchor_watch(lhs_anchor)

    tracer.start_anchored()
    try:
        exec(compile(source, str(path), "exec"), {})
    finally:
        tracer.stop()

    assert len(records) == 2
    records.sort(key=lambda r: r.seq_num)

    assert [r.anchor.line for r in records] == [rhs_line, lhs_line]
    assert records[0].value == 1
    assert records[1].value == 2
    assert records[0].seq_num == 0
    assert records[1].seq_num == 1
    assert records[0].logical_order == 0
    assert records[1].logical_order == 0
