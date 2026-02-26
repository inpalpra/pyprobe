import time
import pytest
from PyQt6.QtCore import QObject, pyqtSignal
from pyprobe.report.step_recorder import StepRecorder


# ── Minimal Qt signal emitter for testing ─────────────────────────────────────

class _Emitter(QObject):
    """Minimal QObject used to create real Qt signals in tests."""
    fired = pyqtSignal()
    fired_with_str = pyqtSignal(str)


# ── Lifecycle tests ───────────────────────────────────────────────────────────

def test_recorder_starts_inactive():
    """StepRecorder.is_recording is False immediately after construction."""
    recorder = StepRecorder()
    assert recorder.is_recording is False


def test_start_sets_is_recording_true():
    """After recorder.start(), is_recording is True."""
    recorder = StepRecorder()
    recorder.start()
    assert recorder.is_recording is True


def test_stop_sets_is_recording_false():
    """After start(); stop(), is_recording is False."""
    recorder = StepRecorder()
    recorder.start()
    recorder.stop()
    assert recorder.is_recording is False


# ── record() behaviour tests ──────────────────────────────────────────────────

def test_record_step_appends_when_active():
    """record('did X') appends a RecordedStep while recording is active."""
    recorder = StepRecorder()
    recorder.start()
    recorder.record("did X")
    assert len(recorder.steps) == 1
    assert recorder.steps[0].description == "did X"


def test_record_step_increments_seq_num():
    """Consecutive record() calls produce seq_num values 1, 2, 3, …"""
    recorder = StepRecorder()
    recorder.start()
    recorder.record("one")
    recorder.record("two")
    recorder.record("three")
    assert [s.seq_num for s in recorder.steps] == [1, 2, 3]


def test_record_step_has_timestamp():
    """RecordedStep.timestamp is close to time.time() at call time."""
    recorder = StepRecorder()
    recorder.start()
    before = time.time()
    recorder.record("now")
    after = time.time()
    assert before <= recorder.steps[0].timestamp <= after


def test_record_ignored_when_inactive_before_start():
    """record() before start() produces no steps."""
    recorder = StepRecorder()
    recorder.record("too early")
    assert len(recorder.steps) == 0


def test_record_ignored_after_stop():
    """record() after stop() does not append any steps."""
    recorder = StepRecorder()
    recorder.start()
    recorder.record("during")
    recorder.stop()
    recorder.record("after")
    assert len(recorder.steps) == 1
    assert recorder.steps[0].description == "during"


# ── clear() tests ─────────────────────────────────────────────────────────────

def test_clear_resets_steps_and_seq_num():
    """clear() empties steps and resets seq_num so the next record gets seq_num=1."""
    recorder = StepRecorder()
    recorder.start()
    recorder.record("a")
    recorder.record("b")
    recorder.clear()
    assert len(recorder.steps) == 0
    recorder.record("c")
    assert recorder.steps[0].seq_num == 1


# ── connect_signal() tests ────────────────────────────────────────────────────

def test_connect_signal_records_step_when_active(qtbot):
    """connect_signal(signal, 'did X') produces a step when the signal fires during recording."""
    emitter = _Emitter()
    recorder = StepRecorder()
    recorder.connect_signal(emitter.fired, "did X")
    recorder.start()
    emitter.fired.emit()
    assert len(recorder.steps) == 1
    assert recorder.steps[0].description == "did X"


def test_connect_signal_ignored_when_inactive(qtbot):
    """Signal firing before start() produces no steps."""
    emitter = _Emitter()
    recorder = StepRecorder()
    recorder.connect_signal(emitter.fired, "too early")
    emitter.fired.emit()
    assert len(recorder.steps) == 0


def test_connect_signal_with_formatter_callable(qtbot):
    """connect_signal(signal, fn) uses fn(*args) as the step description."""
    emitter = _Emitter()
    recorder = StepRecorder()
    recorder.connect_signal(emitter.fired_with_str, lambda s: f"received: {s}")
    recorder.start()
    emitter.fired_with_str.emit("hello")
    assert recorder.steps[0].description == "received: hello"


# ── Signal lifecycle tests (critical) ─────────────────────────────────────────

def test_stop_disconnects_signals(qtbot):
    """After stop(), signals that were connected no longer produce steps,
    even if those signals continue to fire."""
    emitter = _Emitter()
    recorder = StepRecorder()
    recorder.connect_signal(emitter.fired, "ping")
    recorder.start()
    emitter.fired.emit()
    assert len(recorder.steps) == 1

    recorder.stop()
    emitter.fired.emit()  # must not add to steps
    assert len(recorder.steps) == 1  # unchanged


def test_start_twice_does_not_duplicate_connections(qtbot):
    """Calling start() twice does not cause a single signal emission to record two steps."""
    emitter = _Emitter()
    recorder = StepRecorder()
    recorder.connect_signal(emitter.fired, "ping")
    recorder.start()
    recorder.start()  # second start — must not double-connect
    emitter.fired.emit()
    assert len(recorder.steps) == 1  # not 2


# ── Snapshot / isolation tests ────────────────────────────────────────────────

def test_steps_frozen_at_stop():
    """steps after stop() is a snapshot; subsequent record() calls have no effect."""
    recorder = StepRecorder()
    recorder.start()
    recorder.record("before stop")
    snapshot = recorder.stop()
    recorder.record("after stop")  # must not appear
    # The returned value from stop() (if any) and the steps property agree
    assert len(recorder.steps) == 1
    assert recorder.steps[0].description == "before stop"


def test_recorder_instances_are_independent():
    """Two StepRecorder instances share no state whatsoever."""
    r1 = StepRecorder()
    r2 = StepRecorder()
    r1.start()
    r1.record("r1 step")
    assert len(r2.steps) == 0


# ── Performance test ──────────────────────────────────────────────────────────

@pytest.mark.performance
def test_overhead_when_inactive_is_negligible():
    """Calling record() 10,000 times on an inactive recorder completes in under 20 ms.

    This guards against accidentally adding work to the hot-path of an inactive recorder.

    Marked @pytest.mark.performance — exclude in constrained CI with:
        pytest -m 'not performance'
    """
    recorder = StepRecorder()  # not started
    start = time.monotonic()
    for _ in range(10_000):
        recorder.record("ignored")
    elapsed = (time.monotonic() - start) * 1000  # ms
    assert elapsed < 20, f"Inactive recorder overhead: {elapsed:.1f}ms, expected < 20ms"
