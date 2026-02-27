import json

from pyprobe.report.report_model import BugReport, OpenFileEntry, RecordedStep
from pyprobe.report.sanitizer import PathSanitizer


class ReportFormatter:
    def __init__(self, max_file_bytes: int = 50 * 1024) -> None:
        self._max_file_bytes = max_file_bytes

    def render(
        self,
        report: BugReport,
        llm_mode: bool = False,
        include_full_file: bool = True,
    ) -> str:
        if not llm_mode:
            return self._render_default(report, include_full_file)
        return self._render_llm(report, include_full_file)

    def _render_default(self, report: BugReport, include_full_file: bool = True) -> str:
        parts: list[str] = []

        parts.append("=== Bug Report ===")
        parts.append(report.description)

        if report.baseline_state is not None:
            parts.append("\n--- Baseline State ---")
            state = report.baseline_state
            if state.open_files:
                parts.append("  Open files:")
                for entry in state.open_files:
                    parts.append(f"    {entry.path}")
            if state.probed_traces:
                parts.append("  Probes:")
                for t in state.probed_traces:
                    parts.append(f"    {t.symbol} ({t.dtype}, shape={t.shape})")
            if state.equations:
                parts.append("  Equations:")
                for eq in state.equations:
                    parts.append(f"    {eq.eq_id}: {eq.expression} [{eq.status}]")
            if state.graph_widgets:
                parts.append("  Widgets:")
                for w in state.graph_widgets:
                    parts.append(f"    {w.widget_id}: {w.lens}")

        if report.steps is not None:
            parts.append("\n--- Steps ---")
            for step in report.steps:
                parts.append(f"{step.seq_num}. {step.description}")

        if report.open_files is not None:
            parts.append("\n--- Open Files ---")
            for entry in report.open_files:
                flags = []
                if entry.is_probed:
                    flags.append("probed")
                if entry.is_executed:
                    flags.append("executed")
                if entry.has_unsaved:
                    flags.append("unsaved")
                flag_str = ", ".join(flags) if flags else "none"
                parts.append(f"  {entry.path} [{flag_str}]")
                if entry.contents is not None:
                    if include_full_file:
                        parts.append(self._render_contents(entry))
                    else:
                        self._append_snippet_windows(
                            parts, entry, report.steps
                        )

        if report.environment is not None:
            parts.append("\n--- Environment ---")
            for key, value in report.environment.items():
                parts.append(f"  {key}: {value}")

        if report.logs is not None:
            parts.append("\n--- Logs ---")
            parts.append(report.logs)

        output = "\n".join(parts)
        return PathSanitizer.sanitize(output)

    def _render_llm(self, report: BugReport, include_full_file: bool) -> str:
        parts: list[str] = []

        parts.append("=== Bug Report ===")
        parts.append(report.description)

        if report.baseline_state is not None:
            parts.append("\n--- Baseline State ---")
            state = report.baseline_state
            if state.open_files:
                parts.append("  Open files:")
                for entry in state.open_files:
                    parts.append(f"    {entry.path}")
            if state.probed_traces:
                parts.append("  Probes:")
                for t in state.probed_traces:
                    parts.append(f"    {t.symbol} ({t.dtype}, shape={t.shape})")
            if state.equations:
                parts.append("  Equations:")
                for eq in state.equations:
                    parts.append(f"    {eq.eq_id}: {eq.expression} [{eq.status}]")
            if state.graph_widgets:
                parts.append("  Widgets:")
                for w in state.graph_widgets:
                    parts.append(f"    {w.widget_id}: {w.lens}")

        if report.steps is not None:
            parts.append("\n--- Steps ---")
            for step in report.steps:
                parts.append(f"{step.seq_num}. {step.description}")
            parts.append("")
            parts.append("Location format: <symbol> @ <file>:<line>:<column>")

        if report.open_files is not None:
            parts.append("\n--- Open Files ---")
            for entry in report.open_files:
                flags = []
                if entry.is_probed:
                    flags.append("probed")
                if entry.is_executed:
                    flags.append("executed")
                if entry.has_unsaved:
                    flags.append("unsaved")
                flag_str = ", ".join(flags) if flags else "none"
                parts.append(f"  {entry.path} [{flag_str}]")

                if entry.contents is not None:
                    if include_full_file:
                        parts.append(self._render_numbered_contents(entry))
                    else:
                        self._append_snippet_windows(
                            parts, entry, report.steps, numbered=True
                        )

        if report.environment is not None:
            parts.append("\n--- Environment ---")
            for key, value in report.environment.items():
                parts.append(f"  {key}: {value}")

        if report.logs is not None:
            parts.append("\n--- Logs ---")
            parts.append(report.logs)

        output = "\n".join(parts)
        return PathSanitizer.sanitize(output)

    def _append_snippet_windows(
        self,
        parts: list[str],
        entry: OpenFileEntry,
        steps: tuple[RecordedStep, ...] | None,
        numbered: bool = False,
    ) -> None:
        """Append ±5 line-numbered snippet windows for a file.

        Falls back to full file contents when no referenced lines exist.
        When *numbered* is True, the fallback uses line-numbered format.
        """
        assert entry.contents is not None
        ref_lines = self._extract_referenced_lines(steps)
        file_refs = ref_lines.get(entry.path, [])
        if not file_refs:
            # No references — fall back to full file
            if numbered:
                parts.append(self._render_numbered_contents(entry))
            else:
                parts.append(self._render_contents(entry))
            return
        windows = self._extract_relevant_windows(entry.contents, file_refs)
        for i, (start, end, lines) in enumerate(windows):
            if i > 0:
                parts.append("  ...")
            for ln, text in enumerate(lines, start=start):
                parts.append(f"{ln:>4} | {text}")

    def _extract_referenced_lines(
        self, steps: tuple[RecordedStep, ...] | None,
    ) -> dict[str, list[int]]:
        """Return {filename: sorted_unique_line_numbers} from step descriptions."""
        result: dict[str, set[int]] = {}
        if steps is None:
            return {}
        for step in steps:
            desc = step.description
            at_idx = desc.find(" @ ")
            if at_idx < 0:
                continue
            location = desc[at_idx + 3:]
            # Parse from the right: column, line, filename
            parts = location.rsplit(":", 2)
            if len(parts) != 3:
                continue
            filename, line_str, col_str = parts
            if not line_str.isdigit() or not col_str.isdigit():
                continue
            result.setdefault(filename, set()).add(int(line_str))
        return {k: sorted(v) for k, v in result.items()}

    @staticmethod
    def _extract_relevant_windows(
        file_contents: str,
        referenced_lines: list[int],
        context: int = 5,
    ) -> list[tuple[int, int, list[str]]]:
        """Return [(start_1based, end_1based, lines)] with merged overlapping ranges."""
        all_lines = file_contents.splitlines()
        total = len(all_lines)
        if total == 0:
            return []

        # Build raw ranges
        ranges: list[list[int]] = []
        for line in referenced_lines:
            start = max(1, line - context)
            end = min(total, line + context)
            ranges.append([start, end])

        # Sort and merge
        ranges.sort()
        merged: list[list[int]] = [ranges[0]]
        for start, end in ranges[1:]:
            if start <= merged[-1][1] + 1:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])

        # Extract line slices
        result: list[tuple[int, int, list[str]]] = []
        for start, end in merged:
            result.append((start, end, all_lines[start - 1 : end]))
        return result

    def _render_numbered_contents(self, entry: OpenFileEntry) -> str:
        assert entry.contents is not None
        encoded = entry.contents.encode("utf-8", errors="replace")
        if len(encoded) > self._max_file_bytes:
            content = encoded[: self._max_file_bytes].decode("utf-8", errors="replace")
            truncated = True
            original_bytes = len(encoded)
        else:
            content = entry.contents
            truncated = False
            original_bytes = 0

        lines = content.splitlines()
        numbered = [f"{i:>4} | {line}" for i, line in enumerate(lines, start=1)]
        result = "\n".join(numbered)
        if truncated:
            result += (
                f"\n[truncated: {original_bytes} bytes total,"
                f" showing first {self._max_file_bytes} bytes]"
            )
        return result

    def render_json(self, report: BugReport) -> str:
        """Render BugReport as a deterministic JSON string. Applies PathSanitizer."""
        data: dict = {"description": report.description}

        if report.steps is not None:
            data["steps"] = [
                {
                    "seq_num": s.seq_num,
                    "description": s.description,
                    "timestamp": s.timestamp,
                }
                for s in report.steps
            ]

        if report.baseline_state is not None:
            state = report.baseline_state
            data["baseline_state"] = {
                "open_files": [
                    {
                        "path": e.path,
                        "is_probed": e.is_probed,
                        "is_executed": e.is_executed,
                        "has_unsaved": e.has_unsaved,
                    }
                    for e in state.open_files
                ],
                "probed_traces": [
                    {
                        "symbol": t.symbol,
                        "file": t.file,
                        "line": t.line,
                        "column": t.column,
                        "shape": t.shape,
                        "dtype": t.dtype,
                    }
                    for t in state.probed_traces
                ],
                "equations": [
                    {
                        "eq_id": eq.eq_id,
                        "expression": eq.expression,
                        "status": eq.status,
                        "is_plotted": eq.is_plotted,
                    }
                    for eq in state.equations
                ],
                "graph_widgets": [
                    {
                        "widget_id": w.widget_id,
                        "lens": w.lens,
                        "is_docked": w.is_docked,
                        "is_visible": w.is_visible,
                    }
                    for w in state.graph_widgets
                ],
                "captured_at": state.captured_at,
            }

        if report.open_files is not None:
            data["open_files"] = [
                {
                    "path": e.path,
                    "is_probed": e.is_probed,
                    "is_executed": e.is_executed,
                    "has_unsaved": e.has_unsaved,
                    **({"contents": e.contents} if e.contents is not None else {}),
                }
                for e in report.open_files
            ]

        if report.environment is not None:
            data["environment"] = report.environment

        if report.logs is not None:
            data["logs"] = report.logs

        raw = json.dumps(data, indent=2, sort_keys=True)
        return PathSanitizer.sanitize(raw)

    def _render_contents(self, entry: OpenFileEntry) -> str:
        assert entry.contents is not None
        encoded = entry.contents.encode("utf-8", errors="replace")
        if len(encoded) <= self._max_file_bytes:
            return entry.contents
        truncated = encoded[: self._max_file_bytes].decode("utf-8", errors="replace")
        original_bytes = len(encoded)
        return (
            truncated
            + f"\n[truncated: {original_bytes} bytes total,"
            f" showing first {self._max_file_bytes} bytes]"
        )
