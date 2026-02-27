# Implementation Plan: Upgraded Step Recorder & Scene Graph

## Phase 1: Architectural Decoupling & Schema Definition
- [ ] Task: Define `DataSource` abstract interface
    - [ ] Write failing tests for `DataSource` interface and basic concrete implementations (Probe, Equation)
    - [ ] Implement `DataSource`, `Probe`, and `Equation` classes
    - [ ] Refactor existing `Trace` class to accept `DataSource` instead of hardcoded `Probe`
- [ ] Task: Finalize App Object JSON Schema
    - [ ] Create Pydantic/dataclass models for Tier 1-4 (Probes, Traces, Visual Items, Annotations)
    - [ ] Write tests ensuring serialization to the defined JSON schema
    - [ ] Implement serialization logic for the App Object
- [ ] Task: Shift real/imaginary logic to Visual Layer
    - [ ] Write tests ensuring data arrays maintain native types and visual items handle the split
    - [ ] Implement native type preservation in Traces
    - [ ] Update Plot logic to handle complex-to-real/imag rendering
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Architectural Decoupling & Schema Definition' (Protocol in workflow.md)

## Phase 2: The Native Hook Interceptor Engine
- [ ] Task: Implement Base Interceptor Engine
    - [ ] Write tests for registering and routing native hooks
    - [ ] Implement `InterceptorEngine` class
- [ ] Task: Implement Native Hooks for core UI events
    - [ ] Write tests for capturing `sigSampleClicked` and other native Qt/pyqtgraph signals
    - [ ] Implement hook bindings to the Interceptor Engine
- [ ] Task: Implement explicit Fallback Coordinate Mapping
    - [ ] Write tests for registering and triggering fallback coordinate mappers
    - [ ] Implement manual mapping registry for non-compliant widgets
- [ ] Task: Implement Debouncing Logic
    - [ ] Write tests for 500ms continuous debounce and immediate discrete flush
    - [ ] Implement `Debouncer` utility and integrate with `InterceptorEngine`
- [ ] Task: Conductor - User Manual Verification 'Phase 2: The Native Hook Interceptor Engine' (Protocol in workflow.md)

## Phase 3: The State Snapshot Generators
- [ ] Task: Implement Baseline Generator
    - [ ] Write tests for traversing active windows/plots and generating the Tier 1-4 App Object
    - [ ] Implement `BaselineGenerator` traversing current UI state
- [ ] Task: Implement Delta Generator
    - [ ] Write tests for converting intercepted events into semantic state deltas (e.g., `.val` suffix)
    - [ ] Implement `DeltaGenerator` mapping events to JSON deltas
- [ ] Task: Conductor - User Manual Verification 'Phase 3: The State Snapshot Generators' (Protocol in workflow.md)

## Phase 4: Integration and Zero-Loss Verification
- [ ] Task: Integrate Interceptor and Generators
    - [ ] Write integration tests verifying an event produces a correct Delta JSON
    - [ ] Wire the `InterceptorEngine` output to the `DeltaGenerator`
- [ ] Task: Implement Scene Graph Report Exporter
    - [ ] Write tests for writing the final JSON report to disk
    - [ ] Implement export utility combining Baseline and Deltas
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Integration and Zero-Loss Verification' (Protocol in workflow.md)