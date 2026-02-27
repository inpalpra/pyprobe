# Implementation Plan: Unambiguous Recording Report Schema

## Phase 1: Interaction Discovery & Vocabulary Building
- [x] Task: Create a simple PyProbe graph with multiple traces (real and complex) specifically for interactive discovery. 94ce657
- [x] Task: Conduct an interactive session (with the user) to trigger all possible mouse interactions on the graph widget components (Legends, Line plots, Axes, Graph Area).
- [x] Task: Document the observed interactions, agree upon the nomenclature for traces (e.g., `tr0.val`, `tr1.mag_db`) and interactions, and formalize the vocabulary.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Interaction Discovery & Vocabulary Building' (Protocol in workflow.md) [checkpoint: 9ac9a21]

## Phase 2: Core Schema & Nomenclature Definition [checkpoint: 5bff338]
- [x] Task: Draft the formal JSON schema incorporating the newly agreed-upon interaction vocabulary and hierarchical trace structure. ef08f7a
    - [x] Write schema definition tests validating JSON structure.
    - [x] Implement schema validation using `jsonschema` or equivalent.
- [x] Task: Implement the new trace nomenclature logic to distinguish primary vs overlay traces within `Widget` objects. 92df57e
    - [x] Write unit tests for trace naming and role assignments.
    - [x] Update `Widget` and `Trace` models to reflect primary/overlay relationships and new naming (e.g. `tr1.real`, `tr1.imag`).
- [x] Task: Implement exact probe location tracking (`<symbol> @ <file>:<line>:<column>`) for the baseline state. 92df57e
    - [x] Write unit tests verifying precise file/line/column extraction.
    - [x] Implement the location extraction logic in the tracer module.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Core Schema & Nomenclature Definition' (Protocol in workflow.md) 5bff338

## Phase 3: Event Capture Integration [checkpoint: aa3358e]
- [x] Task: Implement comprehensive interaction logging for all defined graph components. 5bff338
    - [x] Write tests verifying that events (clicks, drags, etc.) emit the correct structure using the new vocabulary.
    - [x] Wire PyProbe's UI components to capture and serialize these interactions as steps.
- [x] Task: Update the reporting engine to serialize the full baseline state and interaction history into the new JSON schema. 1d869e1
    - [x] Write tests for end-to-end report generation using the new schema.
    - [x] Update serialization logic.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Event Capture Integration' (Protocol in workflow.md) aa3358e

## Phase 4: Integration and Final Testing [checkpoint: aa3358e]
- [x] Task: Update the LLM-optimized textual representation to be derived reliably from the new JSON schema. 1d869e1
    - [x] Write tests for textual report generation.
    - [x] Update formatting templates.
- [x] Task: Run full regression test suite. 16757
- [x] Task: Conductor - User Manual Verification 'Phase 4: Integration and Final Testing' (Protocol in workflow.md)