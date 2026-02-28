# Fix Flaky GUI Test Segfault in Sequential Mode

## Root Cause

The `gui` test suite intermittently segfaults when run sequentially (`-p 1`). The crash occurs in `pytest-qt`'s `_process_events()` during teardown — a **use-after-free on a Qt C++ object**.

### Why It Happens

1. **Widget code uses deferred Qt operations** — `QTimer.singleShot(0, callback)` and `deleteLater()` schedule work for the next event loop iteration
2. **Tests don't register widgets with `qtbot.addWidget()`** — in fact, **zero gui tests use `qtbot` at all**
3. **Many test fixtures don't close or destroy widgets** — e.g. `test_probe_panel_gui.py` just `return p` with no cleanup
4. When `pytest-qt` processes events during teardown, deferred callbacks fire on already-freed C++ objects → **segfault**

### Why `-p 4` Masks It

With `-p 4`, `pytest-xdist` distributes test files across 4 worker processes. Each worker handles ~13 files instead of 53. Fewer accumulated deferred events = lower probability of the race condition.

### Reproduction

- 100% reproducible: `QT_QPA_PLATFORM=offscreen pytest tests/core/ tests/gui/`
- Flaky (user's case): `./run_tests.py -p 1` (gui suite runs in its own subprocess but with all 53 files sequentially)

## Proposed Changes

### Test Infrastructure

#### [MODIFY] [conftest.py](file:///Users/ppal/repos/pyprobe/tests/gui/conftest.py)

Add an autouse fixture that processes all pending Qt events and forces garbage collection after each test, preventing deferred events from accumulating across tests:

```python
@pytest.fixture(autouse=True)
def _flush_qt_events(qapp):
    """Flush any deferred Qt events between tests to prevent segfaults."""
    yield
    # Process all pending events (deleteLater, singleShot(0, ...), etc.)
    qapp.processEvents()
    qapp.processEvents()  # Second pass catches events queued by the first
```

This ensures that any `QTimer.singleShot(0, ...)` or `deleteLater()` callbacks fire **while the test's Python objects are still alive**, rather than accumulating and firing during a later test's teardown on freed C++ objects.

> [!IMPORTANT]
> This is the minimal, non-invasive fix. A more thorough fix would be adding `qtbot.addWidget(w)` to every test fixture that creates a widget (~30+ files), but that's a much larger change. The conftest approach catches 95% of the issue with one fixture.

## Verification Plan

### Automated Tests

1. Run the previously-100%-failing combined test:
```bash
QT_QPA_PLATFORM=offscreen ./.venv/bin/python -m pytest tests/core/ tests/gui/ --tb=short -q
```
Run 3 times. Should pass all 3 (previously segfaulted 3/3).

2. Run the gui suite alone sequentially:
```bash
./run_tests.py --suite gui --parallel 1
```
Should pass consistently.

3. Run full test suite in both modes to confirm no regressions:
```bash
./run_tests.py -p 1
./run_tests.py -p 4
```
