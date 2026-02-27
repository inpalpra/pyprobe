from dataclasses import dataclass

@dataclass(frozen=True)
class OpenFileEntry:
    path: str
    is_probed: bool
    is_executed: bool
    has_unsaved: bool
    contents: str | None = None

@dataclass(frozen=True)
class ProbeTraceEntry:
    symbol: str
    file: str
    line: int
    column: int
    shape: tuple[int, ...]
    dtype: str

@dataclass(frozen=True)
class EquationEntry:
    eq_id: str
    expression: str
    status: str
    is_plotted: bool

@dataclass(frozen=True)
class WidgetTraceEntry:
    trace_id: str
    components: tuple[str, ...]

@dataclass(frozen=True)
class GraphWidgetEntry:
    widget_id: str
    is_docked: bool
    is_visible: bool
    lens: str
    primary_trace: WidgetTraceEntry
    overlay_traces: tuple[WidgetTraceEntry, ...]
    legend_entries: tuple[str, ...] = ()

@dataclass(frozen=True)
class RecordedStep:
    seq_num: int
    timestamp: float
    action_type: str
    target_element: str
    modifiers: tuple[str, ...]
    button: str
    description: str


@dataclass(frozen=True)
class SessionState:
    open_files:    tuple[OpenFileEntry, ...]    = ()
    probed_traces: tuple[ProbeTraceEntry, ...]  = ()
    equations:     tuple[EquationEntry, ...]    = ()
    graph_widgets: tuple[GraphWidgetEntry, ...] = ()
    captured_at:   float                        = 0.0


@dataclass(frozen=True)
class BugReport:
    description:    str
    steps:          tuple[RecordedStep, ...] | None  = None
    baseline_state: SessionState | None              = None
    open_files:     tuple[OpenFileEntry, ...] | None = None
    environment:    dict | None                      = None
    logs:           str | None                       = None
