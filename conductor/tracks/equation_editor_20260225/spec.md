# Specification: Equation Editor

## Overview
Implement an Equation Editor similar to those found in Keysight PXA or VNA. This feature allows users to perform mathematical operations on raw probed data (traces) using Python-based expressions. The results of these equations can be plotted as new traces.

## Functional Requirements

### 1. Trace Identification
- Each probed variable (and watch window variable) must be assigned a unique, global ID in the format `tr<n>` (e.g., `tr0`, `tr1`, `tr2`).
- IDs are persistent as long as the variable is probed.
- **ID Reuse:** If a variable is unprobed, its ID is vacated. New variables should first fill vacated IDs (lowest first) before incrementing the highest existing ID.
- Equation results `eq<n>` should also be assignable a `tr` ID (or `eq` ID) so they can be used in other equations.

### 2. Equation Editor UI
- The editor will be implemented as a **Modal Dialog**.
- Features a list of equations.
- A `+` button adds a new row with `eq<n> = ` prefix.
- A text area for entering custom mathematical expressions.
- Support for "Drag and Drop": Users can drag `eq<n>` labels from the editor onto existing graph windows to plot them.
- Support for "Click to Plot": Clicking an equation (or a button next to it) plots the result in a new window.

### 3. Expression Engine
- Equations are evaluated as Python expressions.
- **Scope:** Restricted to `numpy` (as `np`) and common signal processing functions (e.g., `scipy.signal`).
- **Data Integrity:** When a `tr<n>` variable is used in an equation, the raw underlying complex data is used, regardless of how the trace is currently being visualized (lens, phase/mag view, etc.).
- **Recursive Equations:** Equations can reference other equations (e.g., `eq1 = eq0 * 2`).

### 4. Trace Lifecycle
- Equation traces should update in real-time when the underlying `tr<n>` variables change.
- Handling unprobed variables: If an equation depends on a `tr<n>` that is unprobed, the equation should indicate an error or evaluate to null/zero.

## Non-Functional Requirements
- **Performance:** Equation evaluation should be efficient enough to maintain real-time plotting performance.
- **UI Responsiveness:** The dialog should not hang during evaluation.

## Acceptance Criteria
- [ ] Every probed variable is assigned a unique `tr<n>` ID.
- [ ] IDs are reused correctly when variables are unprobed.
- [ ] Equation Editor dialog opens and allows adding/editing equations.
- [ ] Equations correctly use raw data for `tr<n>` variables.
- [ ] Equation results can be dragged into existing windows or plotted in new ones.
- [ ] Recursive equations (equations using other equations) work correctly.

## Out of Scope
- Full Python script execution (restricted to single-line or simple expressions).
- External file imports within equations.