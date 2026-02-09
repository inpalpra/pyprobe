"""Per-probe buffer for complete capture history."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from pyprobe.logging import get_logger
from ..core.anchor import ProbeAnchor
from ..core.capture_record import CaptureRecord

logger = get_logger(__name__)


@dataclass
class ProbeDataBuffer:
    """Store complete capture history for a single probe."""

    anchor: ProbeAnchor
    _values: List[object] = field(default_factory=list, init=False, repr=False)
    _timestamps: List[int] = field(default_factory=list, init=False, repr=False)
    _seq_nums: List[int] = field(default_factory=list, init=False, repr=False)
    _last_dtype: Optional[str] = field(default=None, init=False, repr=False)
    _last_shape: Optional[tuple] = field(default=None, init=False, repr=False)

    def append(self, record: CaptureRecord) -> None:
        """Append a capture record, logging if sequence is out of order."""
        if self._seq_nums and record.seq_num <= self._seq_nums[-1]:
            logger.warning(
                "Out of order capture for %s: seq=%s last=%s",
                self.anchor.short_label(),
                record.seq_num,
                self._seq_nums[-1],
            )

        self._values.append(record.value)
        self._timestamps.append(record.timestamp)
        self._seq_nums.append(record.seq_num)
        self._last_dtype = record.dtype
        self._last_shape = record.shape

    def get_plot_data(self) -> Tuple[List[int], List[object]]:
        """Return timestamps and values for graph rendering."""
        return self._timestamps, self._values

    @property
    def count(self) -> int:
        """Number of captures stored."""
        return len(self._values)

    @property
    def last_seq(self) -> Optional[int]:
        """Last sequence number stored, if any."""
        if not self._seq_nums:
            return None
        return self._seq_nums[-1]

    @property
    def last_value(self) -> Optional[object]:
        """Last value stored, if any."""
        if not self._values:
            return None
        return self._values[-1]

    @property
    def last_dtype(self) -> Optional[str]:
        """Last dtype stored, if any."""
        return self._last_dtype

    @property
    def last_shape(self) -> Optional[tuple]:
        """Last shape stored, if any."""
        return self._last_shape
