"""
State Tracer for PyProbe.

Logs all user actions and system reactions in a structured format:
(State, Action) → (NewState, Reactions)

Usage:
    python -m pyprobe --trace-states examples/dsp_demo.py
    
Logs to /tmp/pyprobe_state_trace.log
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class StateSnapshot:
    """Snapshot of system state at a moment."""
    timestamp: str
    is_running: bool
    is_paused: bool
    loop_enabled: bool
    action_button_text: str
    stop_button_enabled: bool
    script_path: Optional[str]
    active_probes: int
    subprocess_alive: bool
    ipc_valid: bool
    
    def state_name(self) -> str:
        """Return state name: IDLE, EXECUTING, or PAUSED."""
        if not self.is_running:
            return "IDLE"
        elif self.is_paused:
            return "PAUSED"
        else:
            return "EXECUTING"


@dataclass
class TraceEvent:
    """A single trace event."""
    event_id: int
    event_type: str  # ACTION, REACTION, STATE_CHANGE, IPC_MESSAGE
    source: str  # user, system, ipc
    description: str
    before_state: Optional[str] = None
    after_state: Optional[str] = None
    details: dict = field(default_factory=dict)


class StateTracer:
    """
    Traces all state transitions and actions in PyProbe.
    
    Logs:
    - User actions: Run, Pause, Stop, Loop toggle, Probe add/remove
    - System reactions: Subprocess start/end, IPC messages, button updates
    - State changes: IDLE → EXECUTING → PAUSED → IDLE
    """
    
    LOG_FILE = Path("/tmp/pyprobe_state_trace.log")
    
    def __init__(self, enabled: bool = False):
        self._enabled = enabled
        self._event_id = 0
        self._events: list[TraceEvent] = []
        self._start_time = time.time()
        self._main_window = None  # Set by MainWindow
        
        if enabled:
            # Clear and start fresh log
            self.LOG_FILE.write_text("")
            self._log_header()
    
    def set_main_window(self, window):
        """Set reference to MainWindow for state queries."""
        self._main_window = window
        if self._enabled:
            self.trace_initial_state()
    
    def _log_header(self):
        """Write header to log file."""
        header = f"""
================================================================================
PyProbe State Trace Log
Started: {datetime.now().isoformat()}
================================================================================
Format: [TIME] EVENT_TYPE | SOURCE | DESCRIPTION
        State: BEFORE → AFTER
        Details: {{key: value}}
================================================================================

"""
        with open(self.LOG_FILE, "a") as f:
            f.write(header)
    
    def _elapsed(self) -> str:
        """Return elapsed time since start."""
        elapsed = time.time() - self._start_time
        return f"{elapsed:8.3f}s"
    
    def _get_state(self) -> StateSnapshot:
        """Get current state snapshot from MainWindow."""
        if self._main_window is None:
            return StateSnapshot(
                timestamp=self._elapsed(),
                is_running=False,
                is_paused=False,
                loop_enabled=False,
                action_button_text="?",
                stop_button_enabled=False,
                script_path=None,
                active_probes=0,
                subprocess_alive=False,
                ipc_valid=False
            )
        
        mw = self._main_window
        cb = mw._control_bar
        
        return StateSnapshot(
            timestamp=self._elapsed(),
            is_running=mw._is_running,
            is_paused=getattr(mw, '_is_paused', False),
            loop_enabled=cb.is_loop_enabled,
            action_button_text=cb._action_btn.text(),
            stop_button_enabled=cb._stop_btn.isEnabled(),
            script_path=mw._script_path,
            active_probes=len(mw._probe_registry.active_anchors) if hasattr(mw, '_probe_registry') else 0,
            subprocess_alive=mw._runner_process is not None and mw._runner_process.is_alive() if mw._runner_process else False,
            ipc_valid=mw._ipc is not None
        )
    
    def _write_event(self, event: TraceEvent):
        """Write event to log file."""
        if not self._enabled:
            return
            
        self._events.append(event)
        
        lines = [
            f"[{self._elapsed()}] {event.event_type:12} | {event.source:8} | {event.description}"
        ]
        
        if event.before_state or event.after_state:
            lines.append(f"             State: {event.before_state or '?'} → {event.after_state or '?'}")
        
        if event.details:
            details_str = ", ".join(f"{k}={v}" for k, v in event.details.items())
            lines.append(f"             Details: {{{details_str}}}")
        
        lines.append("")
        
        with open(self.LOG_FILE, "a") as f:
            f.write("\n".join(lines))
    
    def trace_initial_state(self):
        """Log initial state when app starts."""
        state = self._get_state()
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="INITIAL",
            source="system",
            description="PyProbe started",
            after_state=state.state_name(),
            details={
                "script": state.script_path or "None",
                "loop": state.loop_enabled
            }
        )
        self._write_event(event)
    
    # === User Action Traces ===
    
    def trace_action_run_clicked(self):
        """User clicked Run button."""
        before = self._get_state()
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="ACTION",
            source="user",
            description="Clicked RUN button",
            before_state=before.state_name(),
            details={"loop_enabled": before.loop_enabled}
        )
        self._write_event(event)
    
    def trace_action_pause_clicked(self):
        """User clicked Pause button."""
        before = self._get_state()
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="ACTION",
            source="user",
            description="Clicked PAUSE button",
            before_state=before.state_name()
        )
        self._write_event(event)
    
    def trace_action_resume_clicked(self):
        """User clicked Resume button."""
        before = self._get_state()
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="ACTION",
            source="user",
            description="Clicked RESUME button",
            before_state=before.state_name()
        )
        self._write_event(event)
    
    def trace_action_stop_clicked(self):
        """User clicked Stop button."""
        before = self._get_state()
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="ACTION",
            source="user",
            description="Clicked STOP button",
            before_state=before.state_name()
        )
        self._write_event(event)
    
    def trace_action_loop_toggled(self, enabled: bool):
        """User toggled Loop button."""
        before = self._get_state()
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="ACTION",
            source="user",
            description=f"Toggled LOOP {'ON' if enabled else 'OFF'}",
            before_state=before.state_name(),
            details={"new_loop_state": enabled}
        )
        self._write_event(event)
    
    def trace_action_probe_added(self, anchor_str: str):
        """User added a probe."""
        before = self._get_state()
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="ACTION",
            source="user",
            description=f"Added probe: {anchor_str}",
            before_state=before.state_name(),
            details={"probe": anchor_str, "total_probes": before.active_probes + 1}
        )
        self._write_event(event)
    
    def trace_action_probe_removed(self, anchor_str: str):
        """User removed a probe."""
        before = self._get_state()
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="ACTION",
            source="user",
            description=f"Removed probe: {anchor_str}",
            before_state=before.state_name()
        )
        self._write_event(event)
    
    # === System Reaction Traces ===
    
    def trace_reaction_subprocess_started(self, pid: int):
        """Subprocess was started."""
        after = self._get_state()
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="REACTION",
            source="system",
            description=f"Subprocess started (PID={pid})",
            after_state=after.state_name(),
            details={"pid": pid, "script": after.script_path}
        )
        self._write_event(event)
    
    def trace_reaction_subprocess_ended(self, exit_code: Optional[int] = None):
        """Subprocess ended."""
        after = self._get_state()
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="REACTION",
            source="system",
            description=f"Subprocess ended (exit_code={exit_code})",
            after_state=after.state_name(),
            details={"exit_code": exit_code}
        )
        self._write_event(event)
    
    def trace_reaction_state_changed(self, reason: str):
        """State changed."""
        after = self._get_state()
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="STATE_CHG",
            source="system",
            description=f"State changed: {reason}",
            after_state=after.state_name(),
            details={
                "is_running": after.is_running,
                "button": after.action_button_text,
                "subprocess_alive": after.subprocess_alive
            }
        )
        self._write_event(event)
    
    def trace_reaction_cleanup(self, reason: str):
        """Cleanup was performed."""
        after = self._get_state()
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="REACTION",
            source="system",
            description=f"Cleanup: {reason}",
            after_state=after.state_name(),
            details={"ipc_valid": after.ipc_valid}
        )
        self._write_event(event)
    
    # === IPC Message Traces ===
    
    def trace_ipc_sent(self, msg_type: str, details: dict = None):
        """IPC message sent."""
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="IPC_SEND",
            source="gui→run",
            description=f"Sent: {msg_type}",
            details=details or {}
        )
        self._write_event(event)
    
    def trace_ipc_received(self, msg_type: str, details: dict = None):
        """IPC message received."""
        after = self._get_state()
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="IPC_RECV",
            source="run→gui",
            description=f"Received: {msg_type}",
            after_state=after.state_name(),
            details=details or {}
        )
        self._write_event(event)
    
    def trace_loop_restart(self, loop_count: int):
        """Loop restart occurred."""
        after = self._get_state()
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="LOOP",
            source="system",
            description=f"Loop restart #{loop_count}",
            after_state=after.state_name(),
            details={
                "loop_count": loop_count,
                "subprocess_alive": after.subprocess_alive
            }
        )
        self._write_event(event)
    
    def trace_error(self, error: str):
        """Error occurred."""
        after = self._get_state()
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="ERROR",
            source="system",
            description=f"Error: {error}",
            after_state=after.state_name()
        )
        self._write_event(event)
    
    def trace_poll_timer(self, messages_processed: int):
        """Poll timer fired (only log if messages were processed)."""
        if messages_processed == 0:
            return  # Don't spam log with empty polls
        
        after = self._get_state()
        self._event_id += 1
        event = TraceEvent(
            event_id=self._event_id,
            event_type="POLL",
            source="system",
            description=f"Poll timer: processed {messages_processed} messages",
            after_state=after.state_name()
        )
        self._write_event(event)
    
    def get_summary(self) -> str:
        """Get summary of all events."""
        if not self._events:
            return "No events recorded"
        
        lines = [
            f"Total events: {len(self._events)}",
            f"Actions: {sum(1 for e in self._events if e.event_type == 'ACTION')}",
            f"Reactions: {sum(1 for e in self._events if e.event_type == 'REACTION')}",
            f"IPC messages: {sum(1 for e in self._events if e.event_type.startswith('IPC'))}",
            f"State changes: {sum(1 for e in self._events if e.event_type == 'STATE_CHG')}",
        ]
        return "\n".join(lines)


# Global tracer instance
_tracer: Optional[StateTracer] = None


def get_tracer() -> StateTracer:
    """Get the global state tracer."""
    global _tracer
    if _tracer is None:
        _tracer = StateTracer(enabled=False)
    return _tracer


def init_tracer(enabled: bool = False) -> StateTracer:
    """Initialize the global state tracer."""
    global _tracer
    _tracer = StateTracer(enabled=enabled)
    return _tracer
