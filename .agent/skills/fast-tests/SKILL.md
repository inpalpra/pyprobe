---
name: fast-tests
description: Guide and strategy for optimizing slow test suites that suffer from subprocess spawning overhead. Use this skill when users want to speed up tests that are slow because each test launches a separate instance of a heavy application or subprocess (like PyProbe, UI instances, or analyzers), and when you need a procedural guide on how to consolidate these tests using a "megascript" or single-pass pattern.
---

# Fast Tests Strategy: The Megascript Pattern

When an end-to-end test suite is slow primarily because each test method spawns its own heavy subprocess (e.g., launching an interpreter, a GUI, or a tracing pipeline), you can achieve 10x-20x speedups by consolidating the execution.

This skill defines two main strategies: the **Megascript Pattern** (for tests that spawn full subprocesses), and the **Module-Scoped Fixture Pattern** (for in-process UI widget tests).

## Strategy 1: The Megascript Pattern (For Subprocess Overhead)

This pattern involves combining individual test payloads into a single execution run, capturing all necessary state at once, and having individual tests simply assert against the pre-computed data.

### Core Strategy

1. **Combine the Payloads:** Take the individual scripts or code snippets that each test previously ran in isolation, and concatenate them into a single large script (the "megascript").
2. **Execute Once:** Use the test framework's class-level setup (e.g., `setUpClass` in `unittest` or module-scoped fixtures in `pytest`) to spawn the heavy subprocess exactly once, running the megascript.
3. **Capture All State:** Instrument the single execution to collect all the data required by all the individual tests and store it in a class-level or module-level dictionary/store.
4. **Assert in Tests:** Modify the individual tests to retrieve the specific data they need from the global store, rather than running the subprocess themselves. The assertions themselves should remain functionally identical.

### Implementation Steps

### 1. Code Generation
Often, it is safer to write a Python script that programmatically generates the new fast test suite by parsing the original slow suite. This prevents manual copy-paste errors and ensures functional equivalency.

### 2. Line numbers and Anchoring
If your testing relies on line numbers (like AST tracing or breakpoints), combine the scripts systematically:
- Wrap each script's logic in its own function within the megascript.
- Inject marker comments (e.g., `# L:test_name:local_line_index`) into the generated megascript.
- At runtime, parse the megascript to map these markers to the absolute line numbers in the generated megascript file so the framework knows where to place probes/breakpoints.

### 3. Execution Infrastructure
When launching the megascript subprocess:
- **Avoid temporary strings:** Rather than maintaining massive Python strings of code and writing them out via `tempfile`, extract the megascript into a static helper file (e.g., `tests/gui/data/temporal_megascript.py`).
- **Load directly:** Pass the absolute path of this helper script to the framework or subprocess directly (`os.path.join(os.path.dirname(__file__), "data", "temporal_megascript.py")`).
- **Use in-memory capture:** For extremely fast test runs, use `subprocess.run(..., capture_output=True, text=True)` to capture streams directly into memory instead of routing them through `tempfile.TemporaryFile`. This eliminates redundant disk I/O, file seeking, and buffering overhead.

### 4. Watch for Hardcoded Delays
When combining testing workflows:
- **Reduce UI wait times:** Repeated arbitrary wait times in helper functions (like `QTest.qWait(500)`) will stack up significantly when testing scenarios sequentially. Check your delays and reduce them to the minimum required for the async framework to process the event loop context (e.g. from 500ms down to 10-20ms).

## Strategy 2: Module-Scoped Fixture Pattern (For In-Process GUI Tests)

If a GUI test suite is slow *not* because of subprocesses, but because it is repeatedly building and destroying complex Qt layout topologies in-process, you do not need a full megascript.

Instead, reuse the same widget instance chronologically across tests:

1. **Promote Fixture:** Change the widget-generating `@pytest.fixture` from function scope to `scope="module"`. The widget is instantiated exactly once per Python execution.
2. **Chronological Structure:** Rethink the test suite as a linear sequence of events applied to the same widget. Data is overwritten logically as the file progresses from top to bottom.
3. **Preserve Renders:** If the test suite specifically verifies visual correctness elements, ensure `qapp.processEvents()` is explicitly called after every data update injected into the widget to guarantee the Pyqtgraph render cycle flushes and completes. Avoid eliminating `processEvents` entirely, as that only tests internal memory arrays rather than physical Qt screen buffers.

## Definition of Done

A test suite optimization using this pattern is considered **Done** when:

1. **Performance:** The test suite execution time is drastically reduced (e.g., 90%+ improvement) due to the elimination of repeated startup/teardown overhead.
2. **Parity:** No tests were functionally dropped. Every test that existed in the slow suite exists in the fast suite.
3. **Assertion Integrity:** The actual `assertEqual`, `assertTrue`, etc., statements inside the test methods remain identical. We only change *how* the data is fetched, not *what* data is expected.
4. **Isolation:** Tests do not cross-pollinate. By wrapping each script payload in its own isolated function inside the megascript, variable namespace collisions are avoided.
5. **Stability:** The test runner successfully runs the suite without intermittent crashes or hanging processes. All subprocess streams/IPC channels are cleanly closed in `tearDownClass`.
6. **Graceful Replacement:** The old slow test file is disabled by appending the `.disabled` extension, ensuring it isn't accidentally run by `pytest` or CI.

## Important
Always use python from ./.venv/bin/python