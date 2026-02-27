"""
StepRecorder — accumulates RecordedStep objects by recording method calls
or Qt signal emissions.  Zero overhead when inactive.

No PyQt6 import at module level (keeps this importable without a display).
"""

import time
from typing import Callable

from pyprobe.report.report_model import RecordedStep


class StepRecorder:
    """Records user-visible steps as RecordedStep objects.

    Lifecycle:
        recorder = StepRecorder()
        recorder.connect_signal(some_signal, "description")
        recorder.start()
        # ... signals fire and/or recorder.record("manual step") is called
        steps = recorder.stop()  # returns frozen tuple
    """

    def __init__(self) -> None:
        self._is_recording: bool = False
        self._steps: list[RecordedStep] = []
        self._seq_num: int = 0
        self._connections: list[tuple] = []  # (signal, slot) pairs for cleanup

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def steps(self) -> tuple[RecordedStep, ...]:
        return tuple(self._steps)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Activate recording.  Calling start() twice is a no-op (no duplicate connections)."""
        if self._is_recording:
            return
        self._is_recording = True

    def stop(self) -> tuple[RecordedStep, ...]:
        """Deactivate recording and return frozen snapshot.

        Signals remain connected — they are no-ops while ``_is_recording``
        is False.  Use :meth:`disconnect_all` for explicit teardown.
        """
        self._is_recording = False
        return tuple(self._steps)

    def disconnect_all(self) -> None:
        """Disconnect all connected signals.  Called during teardown."""
        for signal, slot in self._connections:
            try:
                signal.disconnect(slot)
            except Exception:
                pass  # already disconnected or emitter deleted — safe to ignore
        self._connections.clear()

    def clear(self) -> None:
        """Empty the step list and reset seq_num.  Recording state is unchanged."""
        self._steps.clear()
        self._seq_num = 0

    # ── Recording ─────────────────────────────────────────────────────────────

    def record(self, description: str, action_type: str = "Unknown", target_element: str = "Unknown", modifiers: tuple[str, ...] = (), button: str = "None") -> None:
        """Append a RecordedStep if currently recording.  No-op otherwise.
        
        Duplicate consecutive steps with the same description are ignored to
        reduce noise in the final report.
        """
        if not self._is_recording:
            return
            
        # Skip duplicate consecutive steps
        if self._steps and self._steps[-1].description == description:
            return

        self._seq_num += 1
        self._steps.append(
            RecordedStep(
                seq_num=self._seq_num,
                timestamp=time.time(),
                action_type=action_type,
                target_element=target_element,
                modifiers=modifiers,
                button=button,
                description=description,
            )
        )

    # ── Signal connection ─────────────────────────────────────────────────────

    def connect_signal(
        self,
        signal,
        description: str | Callable[..., str],
    ) -> None:
        """Connect a Qt signal so that each emission records a step.

        Args:
            signal: Any Qt signal (duck-typed — no PyQt6 import required here).
            description: Either a fixed string or a callable that receives the
                signal's arguments and returns a description string.
        """
        if callable(description):
            formatter = description
            def slot(*args):  # noqa: E306
                self.record(formatter(*args))
        else:
            fixed = description
            def slot(*args):  # noqa: E306
                self.record(fixed)

        signal.connect(slot)
        self._connections.append((signal, slot))
