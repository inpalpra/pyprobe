import heapq

class WindowIDManager:
    """
    Manages allocation and reuse of unique window IDs (w0, w1, etc.).
    """
    def __init__(self):
        self.released_ids = []  # Min-heap of available integer indices
        self.next_id_idx = 0

    def allocate(self) -> str:
        """
        Allocates a unique w<n> ID.
        """
        if self.released_ids:
            idx = heapq.heappop(self.released_ids)
        else:
            idx = self.next_id_idx
            self.next_id_idx += 1

        return f"w{idx}"

    def release(self, window_id: str) -> None:
        """
        Releases the ID associated with a window.
        """
        if not window_id.startswith("w"):
            return
        
        try:
            idx = int(window_id[1:])  # Extract numeric part of 'w<n>'
            heapq.heappush(self.released_ids, idx)
        except ValueError:
            pass
