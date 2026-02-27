# Implementation Plan: Unambiguous Recording Report Schema

## Phase 1: Interaction Discovery & Vocabulary Building
- [x] Task: Create a simple PyProbe graph with multiple traces (real and complex) specifically for interactive discovery. 94ce657
- [x] Task: Conduct an interactive session (with the user) to trigger all possible mouse interactions on the graph widget components (Legends, Line plots, Axes, Graph Area).
- [x] Task: Document the observed interactions, agree upon the nomenclature for traces (e.g., `tr0.val`, `tr1.mag_db`) and interactions, and formalize the vocabulary.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Interaction Discovery & Vocabulary Building' (Protocol in workflow.md) [checkpoint: 9ac9a21]

## Phase 2: Core Schema & Nomenclature Definition
- [x] Task: Draft the formal JSON schema incorporating the newly agreed-upon interaction vocabulary and hierarchical trace structure. ef08f7a
    - [x] Write schema definition tests validating JSON structure.
    - [x] Implement schema validation using `jsonschema` or equivalent.
- [ ] Task: Implement the new trace nomenclature logic to distinguish primary vs overlay traces within `Widget` objects.
    - [ ] Write unit tests for trace naming and role assignments.
    - [ ] Update `Widget` and `Trace` models to reflect primary/overlay relationships and new naming (e.g. `tr1.real`, `tr1.imag`).
- [ ] Task: Implement exact probe location tracking (`<symbol> @ <file>:<line>:<column>`) for the baseline state.
    - [ ] Write unit tests verifying precise file/line/column extraction.
    - [ ] Implement the location extraction logic in the tracer module.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Core Schema & Nomenclature Definition' (Protocol in workflow.md)

## Phase 3: Event Capture Integration
- [ ] Task: Implement comprehensive interaction logging for all defined graph components.
    - [ ] Write tests verifying that events (clicks, drags, etc.) emit the correct structure using the new vocabulary.
    - [ ] Wire PyProbe's UI components to capture and serialize these interactions as steps.
- [ ] Task: Update the reporting engine to serialize the full baseline state and interaction history into the new JSON schema.
    - [ ] Write tests for end-to-end report generation using the new schema.
    - [ ] Update serialization logic.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Event Capture Integration' (Protocol in workflow.md)

## Phase 4: Integration and Final Testing
- [ ] Task: Update the LLM-optimized textual representation to be derived reliably from the new JSON schema.
    - [ ] Write tests for textual report generation.
    - [ ] Update formatting templates.
- [ ] Task: Run full regression test suite.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Integration and Final Testing' (Protocol in workflow.md)