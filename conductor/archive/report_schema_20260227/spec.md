# Specification: Unambiguous Recording Report Schema & Interaction Vocabulary

## Overview
Improve the PyProbe recording report to ensure forensic-grade reproducibility and eliminate ambiguity. The current reporting of probes and widgets lacks sufficient detail regarding file locations, primary vs. overlay traces, and detailed mouse interactions. This track will define a new, rigorous nomenclature and JSON-based schema to unambiguously describe the baseline state and all user interactions.

## Functional Requirements
1.  **JSON Schema:** The recording report (baseline state and steps) must be structured using a clear, machine-readable JSON schema.
2.  **Unambiguous Probe Locations:** Probes must include precise file, line, and column information (e.g., `<symbol> @ <file>:<line>:<column>`).
3.  **Hierarchical Trace Structure:** Widget descriptions must explicitly distinguish between the primary trace and overlaid traces.
    - Example: `w0` is a complex data widget. It has `tr0` (real valued) as the primary trace, and `tr1` (complex valued) as an overlay.
    - Clear nomenclature for individual plots within a trace: `tr0.val`, `tr1.real`, `tr1.imag`, `tr1.mag_db`, `tr1.phase_deg`.
4.  **Comprehensive Interaction Logging:** Any attempt to interact with any part of a graph widget (Legends, Line plots, Axes, Graph Area, etc.) must be faithfully recorded, regardless of whether it results in a state change. The logging must use clear semantics from a well-defined vocabulary to "provide eyes to an otherwise blind audience or LLM."
5.  **Interaction Discovery & Vocabulary Building:** Conduct interactive testing with a simple graph to capture all possible mouse interactions (clicks, alt-clicks, right-clicks, dragging on legends, axes, line plots, etc.) to build and agree upon the interaction vocabulary before finalizing the schema.

## Non-Functional Requirements
-   **Forensic Reproducibility:** The new schema must allow an LLM or human to perfectly reconstruct the sequence of events and the resulting visual state.

## Acceptance Criteria
- [ ] A formal JSON schema is defined for the recording report.
- [ ] The trace nomenclature unambiguously handles real, complex, primary, and overlay traces.
- [ ] An interactive discovery session is completed to map all PyProbe graph widget interactions.
- [ ] The interaction vocabulary is documented and integrated into the schema.
- [ ] The reporting system is updated to produce reports conforming to the new schema and vocabulary.

## Out of Scope
- Modifying the core visual rendering engine (pyqtgraph) beyond what's needed to capture events.