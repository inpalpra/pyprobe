# AI Problem Solving Lessons: Event Bubbling and Library Introspection

This document captures the workflow, approach, and transferable skills used to solve a difficult GUI event-handling bug in PyProbe involving `pyqtgraph`. It is designed as a learning resource for AI agents (like Gemini Flash) to improve their debugging strategies.

## The Problem Context
**The Bug:** In PyProbe, clicking a plot trace's label in the legend successfully toggled its visibility and recorded a step. However, clicking the "indicator line" (the color swatch/sample next to the label) visually toggled the trace but *failed* to trigger the custom event handler, meaning the action wasn't recorded.
**The Trap:** Previous attempts failed because they assumed the parent `LegendItem`'s `mouseClickEvent` could catch all clicks inside its bounding box, focusing entirely on coordinate mapping and geometry checks.

## The Successful Approach

Instead of guessing why coordinates weren't matching, the successful workflow relied on **isolation, runtime introspection, and understanding GUI event bubbling.**

### Step 1: Isolation via Minimal Reproduction
Rather than debugging inside the massive PyProbe application, we created a 30-line standalone Python script (`test_indicator.py`) containing only a `QApplication`, a `PlotWidget`, and the custom `RemovableLegendItem`. 
* **Why this works:** It removes all noise (state managers, step recorders, complex UI layouts) and proves whether the core assumption about the library is correct.

### Step 2: Runtime Introspection of Third-Party Code
When the click on the sample still didn't trigger the parent's event handler in the isolated script, we stopped guessing and looked at `pyqtgraph`'s source code dynamically.
Using shell commands like:
```bash
python -c "import inspect; import pyqtgraph as pg; print(inspect.getsource(pg.graphicsItems.LegendItem.ItemSample.mouseClickEvent))"
```
* **The Discovery:** We found that `ItemSample` (the color swatch) has its *own* `mouseClickEvent`. It handles the click, toggles the trace visibility natively, calls `event.accept()`, and emits a custom signal (`sigClicked`).
* **Why this works:** You cannot deduce internal library behavior just by looking at the API surface. Reading the source code reveals the exact mechanism.

### Step 3: Understanding Event Bubbling
In Qt (and most UI frameworks like DOM/Browser), events bubble up from child to parent. If a child widget handles an event and calls `accept()`, the parent *never receives that event*.
* **The Realization:** Our parent `RemovableLegendItem` was never getting the click event for the sample because the child `ItemSample` was swallowing it. 

### Step 4: Embracing Native Hooks
Instead of fighting the framework (e.g., trying to disable `ItemSample`'s event handling or doing complex global event filtering), we hooked into the mechanism the library provided.
* **The Fix:** We simply connected to the `sigSampleClicked` signal that the parent `LegendItem` naturally forwards from the `ItemSample`. 

### Step 5: Fixing the Test Suite (Mock Types)
When fixing tests, the test harness threw a `TypeError: arguments did not match any overloaded call`.
* **The Cause:** The test passed a generic `MagicMock` as the simulated mouse position to a Qt function (`mapFromItem`) that strictly expected a `QPointF`.
* **The Fix:** Ensuring mocks respect the strict typing of underlying C++ extensions (like PyQt/PySide).

---

## Transferable Skills for AI Agents

1. **Don't Guess, Introspect:** If a third-party library behaves unexpectedly, write a one-liner to print its `__dict__`, `__bases__`, or use `inspect.getsource()` to read its exact logic.
2. **Build Minimal Repros:** Do not try to debug complex UI interactions in a heavy application state. Write a quick shell script to isolate the one component.
3. **Respect GUI Event Bubbling:** If an expected mouse or keyboard event isn't firing on a parent container, assume a child component is intercepting and swallowing it. Look for child event handlers.
4. **Follow the Path of Least Resistance:** If a framework is natively handling an action (like toggling visibility), don't try to reimplement it. Look for the signal it emits when it finishes the action.
5. **Strict Typing in Mocks:** When testing Qt or other C++ bound libraries, `MagicMock` is often not enough for arguments passed into C++ functions. Use real objects (like `QPointF`) for geometry/position arguments.