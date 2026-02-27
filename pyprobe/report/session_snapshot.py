import dataclasses
import time
from typing import Callable, Iterable

from pyprobe.report.report_model import (
    EquationEntry,
    GraphWidgetEntry,
    OpenFileEntry,
    ProbeTraceEntry,
    SessionState,
)
from pyprobe.report.sanitizer import PathSanitizer


class SessionStateCollector:
    def __init__(
        self,
        file_getter:     Callable[[], Iterable] = lambda: (),
        probe_getter:    Callable[[], Iterable] = lambda: (),
        equation_getter: Callable[[], Iterable] = lambda: (),
        widget_getter:   Callable[[], Iterable] = lambda: (),
    ) -> None:
        self._file_getter = file_getter
        self._probe_getter = probe_getter
        self._equation_getter = equation_getter
        self._widget_getter = widget_getter

    def collect(self) -> SessionState:
        try:
            raw_files = self._file_getter() or ()
            open_files: tuple[OpenFileEntry, ...] = tuple(
                dataclasses.replace(e, path=PathSanitizer.sanitize(e.path))
                for e in raw_files
            )
        except Exception:
            open_files = ()

        try:
            raw_probes = self._probe_getter() or ()
            probed_traces: tuple[ProbeTraceEntry, ...] = tuple(
                dataclasses.replace(e, file=PathSanitizer.sanitize(e.file))
                for e in raw_probes
            )
        except Exception:
            probed_traces = ()

        try:
            raw_equations = self._equation_getter() or ()
            equations: tuple[EquationEntry, ...] = tuple(raw_equations)
        except Exception:
            equations = ()

        try:
            raw_widgets = self._widget_getter() or ()
            graph_widgets: tuple[GraphWidgetEntry, ...] = tuple(raw_widgets)
        except Exception:
            graph_widgets = ()

        return SessionState(
            open_files=open_files,
            probed_traces=probed_traces,
            equations=equations,
            graph_widgets=graph_widgets,
            captured_at=time.time(),
        )
