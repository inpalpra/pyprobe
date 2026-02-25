import heapq

class TraceIDManager:
    """
    Manages allocation and reuse of unique trace IDs (tr0, tr1, etc.).
    """
    def __init__(self):
        self.var_to_id = {}
        self.id_to_var = {}
        self.released_ids = []  # Min-heap of available integer indices
        self.next_id_idx = 0

    def allocate(self, var_name: str) -> str:
        """
        Allocates a unique tr<n> ID for a variable.
        If the variable already has an ID, returns it.
        """
        if var_name in self.var_to_id:
            return self.var_to_id[var_name]

        if self.released_ids:
            idx = heapq.heappop(self.released_ids)
        else:
            idx = self.next_id_idx
            self.next_id_idx += 1

        trace_id = f"tr{idx}"
        self.var_to_id[var_name] = trace_id
        self.id_to_var[trace_id] = var_name
        return trace_id

    def release(self, var_name: str) -> None:
        """
        Releases the ID associated with a variable.
        """
        if var_name not in self.var_to_id:
            return

        trace_id = self.var_to_id.pop(var_name)
        self.id_to_var.pop(trace_id)
        
        idx = int(trace_id[2:])  # Extract numeric part of 'tr<n>'
        heapq.heappush(self.released_ids, idx)

    @property
    def allocated_ids(self) -> dict:
        """
        Returns a mapping of variable names to their allocated trace IDs.
        """
        return self.var_to_id.copy()
