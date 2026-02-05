"""
Message protocol for GUI <-> Runner communication.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional
import time


class MessageType(Enum):
    """Types of messages exchanged between processes."""

    # GUI -> Runner commands
    CMD_ADD_WATCH = auto()      # Add variable to watch list
    CMD_REMOVE_WATCH = auto()   # Remove variable from watch list
    CMD_SET_THROTTLE = auto()   # Update throttle settings
    CMD_PAUSE = auto()          # Pause script execution
    CMD_RESUME = auto()         # Resume script execution
    CMD_STOP = auto()           # Stop script execution

    # Runner -> GUI data
    DATA_VARIABLE = auto()      # Variable value update
    DATA_STDOUT = auto()        # Captured stdout
    DATA_STDERR = auto()        # Captured stderr
    DATA_EXCEPTION = auto()     # Exception occurred
    DATA_SCRIPT_END = auto()    # Script finished
    DATA_SCRIPT_START = auto()  # Script started

    # M1: Anchor-based probe commands
    CMD_ADD_PROBE = auto()      # Add probe by anchor
    CMD_REMOVE_PROBE = auto()   # Remove probe by anchor
    DATA_PROBE_VALUE = auto()   # Probe data with anchor context


@dataclass
class Message:
    """A message exchanged between GUI and Runner processes."""
    msg_type: MessageType
    payload: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if self.payload is None:
            self.payload = {}


# Factory functions for common messages

def make_add_watch_cmd(
    var_name: str,
    throttle_ms: float = 50.0,
    strategy: str = 'time_based'
) -> Message:
    """Create an ADD_WATCH command message."""
    return Message(
        msg_type=MessageType.CMD_ADD_WATCH,
        payload={
            'var_name': var_name,
            'throttle_ms': throttle_ms,
            'strategy': strategy
        }
    )


def make_remove_watch_cmd(var_name: str) -> Message:
    """Create a REMOVE_WATCH command message."""
    return Message(
        msg_type=MessageType.CMD_REMOVE_WATCH,
        payload={'var_name': var_name}
    )


def make_variable_data_msg(
    var_name: str,
    value: Any,
    dtype: str,
    shape: Optional[tuple],
    source_file: str,
    line_number: int,
    function_name: str
) -> Message:
    """Create a VARIABLE data message."""
    return Message(
        msg_type=MessageType.DATA_VARIABLE,
        payload={
            'var_name': var_name,
            'value': value,
            'dtype': dtype,
            'shape': shape,
            'source_file': source_file,
            'line_number': line_number,
            'function_name': function_name
        }
    )


def make_exception_msg(exc_type: str, message: str, traceback: str) -> Message:
    """Create an EXCEPTION data message."""
    return Message(
        msg_type=MessageType.DATA_EXCEPTION,
        payload={
            'type': exc_type,
            'message': message,
            'traceback': traceback
        }
    )


# === M1: Anchor-based probe messages ===

def make_add_probe_cmd(anchor: 'ProbeAnchor', throttle_ms: float = 50.0) -> Message:
    """Create CMD_ADD_PROBE message."""
    return Message(
        msg_type=MessageType.CMD_ADD_PROBE,
        payload={
            'anchor': anchor.to_dict(),
            'throttle_ms': throttle_ms,
        }
    )


def make_remove_probe_cmd(anchor: 'ProbeAnchor') -> Message:
    """Create CMD_REMOVE_PROBE message."""
    return Message(
        msg_type=MessageType.CMD_REMOVE_PROBE,
        payload={'anchor': anchor.to_dict()}
    )


def make_probe_value_msg(
    anchor: 'ProbeAnchor',
    value: Any,
    dtype: str,
    shape: Optional[tuple] = None,
) -> Message:
    """Create DATA_PROBE_VALUE message."""
    return Message(
        msg_type=MessageType.DATA_PROBE_VALUE,
        payload={
            'anchor': anchor.to_dict(),
            'value': value,
            'dtype': dtype,
            'shape': shape,
        }
    )
