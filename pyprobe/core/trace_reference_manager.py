from PyQt6.QtCore import QObject, pyqtSignal

class TraceReferenceManager(QObject):
    """
    Tracks which windows (w0, w1...) are using which trace IDs (tr0, eq0...).
    Emits a signal when a trace is no longer referenced in any window.
    """
    unprobe_signal = pyqtSignal(str)  # Emits trace_id
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = TraceReferenceManager()
        return cls._instance

    def __init__(self):
        super().__init__()
        # trace_id -> set of window_ids
        self.trace_to_windows = {}
        # window_id -> set of trace_ids (for easy cleanup)
        self.window_to_traces = {}

    def add_reference(self, trace_id: str, window_id: str):
        """Adds a reference to trace_id from window_id."""
        if trace_id not in self.trace_to_windows:
            self.trace_to_windows[trace_id] = set()
        self.trace_to_windows[trace_id].add(window_id)

        if window_id not in self.window_to_traces:
            self.window_to_traces[window_id] = set()
        self.window_to_traces[window_id].add(trace_id)

    def remove_reference(self, trace_id: str, window_id: str):
        """Removes a reference to trace_id from window_id."""
        if trace_id in self.trace_to_windows:
            self.trace_to_windows[trace_id].discard(window_id)
            if not self.trace_to_windows[trace_id]:
                del self.trace_to_windows[trace_id]
                self.unprobe_signal.emit(trace_id)

        if window_id in self.window_to_traces:
            self.window_to_traces[window_id].discard(trace_id)

    def get_reference_count(self, trace_id: str) -> int:
        """Returns the number of windows referencing trace_id."""
        return len(self.trace_to_windows.get(trace_id, []))

    def cleanup_window(self, window_id: str):
        """Removes all references from a specific window."""
        if window_id not in self.window_to_traces:
            return

        traces = list(self.window_to_traces[window_id])
        for trace_id in traces:
            self.remove_reference(trace_id, window_id)
        
        if window_id in self.window_to_traces:
            del self.window_to_traces[window_id]
