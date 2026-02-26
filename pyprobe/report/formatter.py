import json

from pyprobe.report.report_model import BugReport, OpenFileEntry
from pyprobe.report.sanitizer import PathSanitizer


class ReportFormatter:
    def __init__(self, max_file_bytes: int = 50 * 1024) -> None:
        self._max_file_bytes = max_file_bytes

    def render(self, report: BugReport) -> str:
        parts: list[str] = []

        parts.append("=== Bug Report ===")
        parts.append(report.description)

        if report.steps is not None:
            parts.append("\n--- Steps ---")
            for step in report.steps:
                parts.append(f"{step.seq_num}. {step.description}")

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
                    parts.append(f"    {t.name} ({t.dtype}, shape={t.shape})")
            if state.equations:
                parts.append("  Equations:")
                for eq in state.equations:
                    parts.append(f"    {eq.eq_id}: {eq.expression} [{eq.status}]")
            if state.graph_widgets:
                parts.append("  Widgets:")
                for w in state.graph_widgets:
                    parts.append(f"    {w.widget_id}: {w.what_plotted}")

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
                    parts.append(self._render_contents(entry))

        if report.environment is not None:
            parts.append("\n--- Environment ---")
            for key, value in report.environment.items():
                parts.append(f"  {key}: {value}")

        if report.logs is not None:
            parts.append("\n--- Logs ---")
            parts.append(report.logs)

        output = "\n".join(parts)
        return PathSanitizer.sanitize(output)

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
                        "name": t.name,
                        "source_file": t.source_file,
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
                        "what_plotted": w.what_plotted,
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
