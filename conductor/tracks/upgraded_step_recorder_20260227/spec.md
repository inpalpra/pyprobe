# Specification: Upgraded Step Recorder & Scene Graph

## Overview
This track defines a multi-milestone plan to implement an upgraded, modular Step Recorder for PyProbe Plots. The objective is to transition from a basic event logger to a "hierarchical scene-graph snapshot" (App Object) for forensic-grade LLM diagnostics. The architecture will decouple tight dependencies (like Probes and Traces) and build a robust, traceable state-capture engine without sacrificing real-time performance.

## Milestones

### Milestone 1: Architectural Decoupling & Schema Definition
*Goal: Define the exact schema for the App Object and decouple foundational concepts.*
- Define the abstract `DataSource` interface to decouple `Traces` from their origins. A `DataSource` can be a `Probe` (direct from code) or an `Equation` (derived data).
- Audit the current schema (Probes, Traces, Visual Items, Annotations) to identify and eliminate other tight couplings.
- Finalize the App Object schema (in JSON format) to ensure it represents a "High-Detail Baseline" for LLM consumption.
- Ensure data arrays maintain their native types (avoiding unnecessary `complex128` overhead) by shifting real/imaginary rendering logic exclusively to the visual layer.

### Milestone 2: The Native Hook Interceptor Engine
*Goal: Build a reliable, non-intrusive event capture system.*
- Implement an interceptor engine that strictly prioritizes Native Hooks (e.g., `sigSampleClicked`) to bypass the "Event Bubbling Trap" from child widgets.
- Implement an explicit, user-directed (or pre-registered) coordinate-mapping fallback system for complex 3rd-party widgets where native hooks fail (no auto-fallback guessing).
- Develop the debouncing logic: Apply a 500ms debounce to continuous inputs (pan/zoom/drag) to capture only the final state, but force an immediate buffer flush upon discrete events (clicks, keypresses) to prevent dropped steps.

### Milestone 3: The State Snapshot Generators
*Goal: Generate the static Baseline and dynamic Deltas.*
- Implement generators that traverse the running application state and output the defined App Object JSON.
- Ensure generators can map physical source locations (Probes) to logical instances (Traces) and ultimately to GUI elements (Visual Items/Plots).
- Ensure generated steps represent precise state deltas and user intent, utilizing standardized suffixes (e.g., `.val`, `.fmag`).

### Milestone 4: Integration and Zero-Loss Verification
*Goal: Tie the modules together and prove the system's reliability.*
- Integrate the Interceptor Engine with the Snapshot Generators.
- Create automated tests to verify "Zero-Loss Recording": ensure all state or visual mutations triggered by known interactions are accurately observed and recorded in the JSON output.

## Out of Scope
- Creating new visualization lenses.
- Modifying the underlying tracer IPC protocol unless required for capturing new state details.