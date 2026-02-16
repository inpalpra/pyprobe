# PROJECT MODE: AI-Driven Structural GUI Testing System

You are a senior systems architect, Qt expert, and AI tooling designer.

I want to design and build an AI-driven GUI testing architecture for a PyQt6-based application (PyProbe). This is NOT visual testing. It is structural, event-driven, introspection-based GUI testing.

The GUI stack:
- PyQt6
- pyqtgraph
- pytest-based test suite
- QTest for event simulation
- Some CLI-based end-to-end automation
- No heavy use of pytest-qt yet (but possible)

The core idea:
I want to enable an LLM (like you) to:
- Understand the GUI codebase
- Reason about widget structure and state transitions
- Generate high-quality UX test specifications
- Map those specifications to real QTest-based tests
- Potentially interact with a live running GUI through a Python REPL
- Eventually evolve into a structured AI GUI testing harness

This is NOT about screenshots.
This is about:
- QObject tree introspection
- Signals / slots
- Properties
- Focus management
- State transitions
- Logs
- Deterministic event simulation

We want to explore feasibility FAST.
If viable, we want to move directly toward a higher-level AI-native testing architecture.

---

# THE VISION

Phase 1:
LLM reads codebase → becomes a "UI/UX Test Architect" → writes complex behavioral test contracts.

Phase 2:
LLM maps those contracts to:
- QTest-based widget tests
- CLI E2E tests
- Or new required test infrastructure

Phase 3:
Add Python REPL-based live interaction:
- LLM can inspect QApplication.instance()
- Traverse QObject tree
- Query objectName, class, properties
- Simulate QTest events live
- Observe logs
- Inspect state
- Iterate

Phase 4 (Next Level):
Design an AIGUITestHarness abstraction:
Instead of raw QTest calls, define structured primitives like:

    press_key("M")
    click("graphWidget")
    assert_property("axisEditor", "visible", True)
    get_signal_count("captureStarted")

Then LLM generates structured test actions instead of ad-hoc Python.

This becomes a domain-specific GUI testing layer optimized for AI.

---

# CONSTRAINTS

- No vision.
- No screenshot diffing.
- Everything must be introspection-based and deterministic.
- Must be realistic for a PyQt6 desktop app.
- Must integrate with pytest.
- Must allow incremental rollout.
- Must allow discovery and learning during implementation.

---

# YOUR TASK

Produce a high-level architectural plan divided into milestones.

Requirements:

1. Define clear milestones.
2. Each milestone should:
   - Have a clear objective.
   - Define deliverables.
   - Define validation criteria.
   - Highlight technical risks.
3. Early milestones should validate feasibility quickly.
4. Later milestones can be more ambitious.
5. Leave room for iteration and refinement.
6. Identify observability requirements (objectName usage, signal exposure, logging improvements, etc.).
7. Explicitly address:
   - How LLM will understand GUI structure.
   - How LLM will generate high-quality UX test contracts.
   - How those contracts map to automation.
   - How REPL-based live interaction would work.
   - What minimal infrastructure is required.
   - What must change in the GUI codebase to support this.
8. Propose an evolution path from:
   QTest scripts → Structured AI test harness.

Do NOT over-specify implementation details.
Do NOT produce code yet.
Focus on system architecture and staged execution.

---

# IMPORTANT

We are willing to aim high early if technically feasible.

If you believe jumping directly toward a structured AI harness (instead of iterating through primitive QTest scripting) is feasible, argue for that.

Be opinionated.
Be strategic.
Highlight where this could fail.
Highlight where it becomes extremely powerful.

Think like someone designing the first serious AI-native GUI testing framework for PyQt.

End with:

- A concise milestone list
- A suggested starting milestone
- A short "first 2-week execution strategy"