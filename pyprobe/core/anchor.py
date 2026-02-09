"""Probe anchor - immutable identity for a probe location."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProbeAnchor:
    """Immutable identity for a probe location in source code.

    Frozen for hashability - can be used as dict key.
    """
    file: str       # Absolute path
    line: int       # 1-indexed line number
    col: int        # Column offset (0-indexed)
    symbol: str     # Variable name at that location
    func: str = ""  # Enclosing function name (optional)
    is_assignment: bool = False  # True if this location is an assignment target (LHS)

    def identity_label(self) -> str:
        """Return human-readable identity: 'symbol @ file:line:col'"""
        filename = self.file.split('/')[-1]  # Just filename, not full path
        return f"{self.symbol} @ {filename}:{self.line}:{self.col}"

    def short_label(self) -> str:
        """Return short label: 'symbol:line'"""
        return f"{self.symbol}:{self.line}"

    def to_dict(self) -> dict:
        """Convert to dict for IPC serialization."""
        return {
            'file': self.file,
            'line': self.line,
            'col': self.col,
            'symbol': self.symbol,
            'func': self.func,
            'is_assignment': self.is_assignment,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'ProbeAnchor':
        """Create from dict (IPC deserialization)."""
        return cls(
            file=d['file'],
            line=d['line'],
            col=d['col'],
            symbol=d['symbol'],
            func=d.get('func', ''),
            is_assignment=d.get('is_assignment', False),
        )
