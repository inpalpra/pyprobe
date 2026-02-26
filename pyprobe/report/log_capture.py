from collections import deque
from dataclasses import dataclass

from pyprobe.report.sanitizer import PathSanitizer

DEFAULT_LOG_PATH = "/tmp/pyprobe_debug.log"
DEFAULT_LINE_COUNT = 200


@dataclass(frozen=True)
class LogSnapshot:
    raw_lines: str
    tracebacks: tuple[str, ...]
    warnings_and_errors: tuple[str, ...]


class LogCapture:
    @classmethod
    def capture(
        cls,
        log_path: str | None = None,
        n: int = DEFAULT_LINE_COUNT,
    ) -> "LogSnapshot | None":
        path = log_path if log_path is not None else DEFAULT_LOG_PATH
        try:
            with open(path, "r", errors="replace") as f:
                tail: deque[str] = deque(f, maxlen=n)
        except Exception:
            return None

        sanitized = [PathSanitizer.sanitize(line) for line in tail]
        raw_lines = "".join(sanitized)

        tracebacks = cls._extract_tracebacks(sanitized)
        warnings_and_errors = tuple(
            line.rstrip("\n")
            for line in sanitized
            if "WARNING" in line or "ERROR" in line
        )

        return LogSnapshot(
            raw_lines=raw_lines,
            tracebacks=tracebacks,
            warnings_and_errors=warnings_and_errors,
        )

    @classmethod
    def _extract_tracebacks(cls, lines: list[str]) -> tuple[str, ...]:
        """Collect each traceback block as a single joined string."""
        blocks: list[str] = []
        i = 0
        while i < len(lines):
            if lines[i].lstrip().startswith("Traceback"):
                block_lines = [lines[i]]
                i += 1
                while i < len(lines):
                    line = lines[i]
                    # Block ends when we hit a non-indented, non-empty line
                    # that is not part of the traceback (i.e. looks like a log line
                    # or is completely empty after the exception message).
                    stripped = line.rstrip("\n")
                    if stripped and not stripped[0].isspace() and i > 0:
                        # Check if it looks like the exception line (no leading space,
                        # non-empty) — include it as the final line of the block.
                        block_lines.append(line)
                        i += 1
                        break
                    block_lines.append(line)
                    i += 1
                blocks.append("".join(block_lines))
            else:
                i += 1
        return tuple(blocks)
