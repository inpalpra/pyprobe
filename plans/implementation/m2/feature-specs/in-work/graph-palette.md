# PyProbe Graph Interaction UX — Requirements Spec (Authoritative)

This document defines REQUIRED behavior for graph interactions in PyProbe.
These are UX contracts, not suggestions. Implement literally unless stated otherwise.

---

## 1. Axis Pinning (Authoritative Semantics)

### Core Rule
- There is **no separate autoscale toggle**.
- **Unpinned axis = always autoscaled**
- **Pinned axis = never autoscaled**

Autoscaling is implicit and continuous unless explicitly overridden by pinning.

### Pin Behavior
- X and Y axes can be pinned independently.
- Pinning an axis:
  - Freezes current scale
  - Disables any future autoscaling on that axis
- Unpinning:
  - Immediately resumes autoscaling

### Visual Indicators
- Pinned axis must be visually obvious:
  - Lock icon (🔒X / 🔒Y) near axis label, OR
  - Axis tick/label style change
- Indicator must be inside the plot area (not toolbar)

### Interaction Rules
- Any manual modification of an axis (zoom, pan, min/max edit) **automatically pins that axis**
- Users may explicitly unpin afterward

---

## 2. Explicit Min / Max Axis Editing (In-Place Only)

### No Dialog Rule
- No modal dialogs
- No popups
- No separate settings panels

### Interaction Model (LabVIEW-style)
- User double-clicks directly on:
  - first tick label → edits minimum
  - last tick label → edits maximum
- Tick label becomes **inline editable text**
- Enter commits value
- Escape cancels edit

### Side Effects
- Editing min or max:
  - Automatically pins that axis
- Clearing pin restores autoscaling

### Visual State
- Axis with explicit bounds must appear pinned
- No separate “explicit range” state exists — pin covers it

---

## 3. Double-Click Maximize / Restore

### Required Behavior
- Double-click anywhere in plot area:
  - Maximizes plot
- Double-click again:
  - Restores previous layout

### Constraints
- No modifier keys (no Shift / Ctrl variants)
- Other plots remain alive and updating
- Grouping, overlays, and probes remain intact

### UX Quality
- Transition must be animated (≈150–200ms)
- Animation is required (not optional polish)

### Hit-Test Priority (Highest → Lowest)

Double-click handling MUST follow this priority order:

1. **Axis Tick Labels (Highest Priority)**
   - Double-click on X or Y axis tick label:
     - Enters in-place edit mode for that value (min or max)
   - Maximize MUST NOT trigger in this case

2. **Axis Line / Axis Region**
   - Double-click on axis line or immediate axis region:
     - No maximize
     - No edit
     - Event is ignored

3. **Plot Background (Low Priority)**
   - Double-click on empty plot background (not data, not axes):
     - Toggles maximize / restore

4. **Plot Data / Traces**
   - Double-click on data traces:
     - MUST NOT trigger maximize
     - Event ignored (reserved for future features)

### Explicit Rules

- Maximize MUST NEVER trigger if the double-click originated on:
  - Axis labels
  - Axis lines
  - Data traces
- Axis editing ALWAYS wins over maximize
- If hit-test target is ambiguous, default to **non-destructive behavior** (do nothing)

### UX Rationale

- Editing scale values is a precision action
- Layout changes are disruptive and must be intentional
- Accidental maximize is considered a UX bug

---

## 4. Minimize (Park) Graphs to Bottom Bar

### Concept
- Graphs are **parked**, not closed or hidden

### Behavior
- Parked graphs:
  - Continue updating
  - Retain probes and state
- Bottom bar shows:
  - Graph title
  - Color key(s)
  - Tiny live sparkline preview

### Interaction
- Click or drag from bottom bar restores graph to main area
- No confirmation dialogs

---

## 5. Overlay Probing (REPLACES Axis Sync Grouping)

Axis sync grouping is **explicitly dropped**.

### Primary Overlay Workflow
1. User probes first symbol → creates a graph
2. User clicks second symbol in code view
3. User drags symbol onto an existing graph
4. Second symbol is plotted **in the same graph**

### Overlay Semantics
- All overlaid signals share the same axes
- Axis operations (pin, min/max, zoom) affect the entire graph
- Each signal:
  - Retains its own color
  - Has its own legend entry
  - Can be removed independently

### Removal
- Removing one signal does NOT remove the graph if others remain
- Removing last signal clears graph

### Drag Feedback
- Valid drop targets must highlight
- Invalid drops must provide brief visual rejection feedback

---

## 6. In-Plot Interaction Buttons (Minimal, Translucent)

### Buttons (inside plot area)
- Hand → pan
- Zoom → arbitrary rectangle
- Zoom X → X axis only
- Zoom Y → Y axis only
- Reset → reset view
- Pointer → default (no interaction)

### Visibility Rules
- Buttons are hidden by default
- Appear only on hover
- Opacity ≤ 40%
- Must never obscure data

### Mode Rules
- Pointer mode is default
- Pan / zoom modes auto-revert to pointer after action
- Escape key always returns to pointer

---

## 7. Keyboard Shortcuts (Required)

These must work when a plot has focus:

- `X` → toggle X-axis pin
- `Y` → toggle Y-axis pin
- `R` → reset view (unpin + autoscale)

No customization required in v1.

---

## 8. Non-Negotiable Interaction Principles

- Manual user action always overrides automation
- Autoscaling must never fight the user
- If user touches an axis, it is pinned
- No hidden modifier gestures
- No modal interruptions
- No state ambiguity

---

## Acceptance Criteria

This UX is considered correct only if:
- Users never wonder why a plot changed scale
- Users never wonder why a plot did NOT change scale
- Overlaying signals feels obvious and discoverable
- Axis behavior is predictable after 5 seconds of use
- The plot feels like a surface, not a widget

Violations require redesign, not documentation.


# PyProbe Plot Interaction — State Diagram (Authoritative)

This diagram defines the legal states and transitions for a single plot.
All interactions must resolve to these states.
If behavior cannot be explained by this diagram, it is a bug.

---

## AXIS STATE MACHINE (X and Y are independent but symmetric)

Each axis exists in exactly ONE of the following states at any time.

      ┌────────────────────┐
      │   AUTO (default)   │
      │  autoscale active  │
      └─────────┬──────────┘
                │
user touches     │
axis (zoom /     │
pan / edit)      │
                ▼
      ┌────────────────────┐
      │       PINNED       │
      │ autoscale disabled │
      └─────────┬──────────┘
                │
    user unpins  │
    (X / Y key   │
     or reset)   │
                ▼
      ┌────────────────────┐
      │   AUTO (default)   │
      └────────────────────┘

### Axis Touch Events (ALL force PINNED)
- Zoom (any type)
- Pan
- In-place min edit
- In-place max edit

### Reset (`R`)
- Unpins axis
- Returns to AUTO
- Autoscale resumes immediately

---

## PLOT VIEW STATE MACHINE (Layout)

        ┌─────────────────────┐
        │      NORMAL         │
        │  part of grid view  │
        └─────────┬───────────┘
                  │
    double-click  │
                  ▼
        ┌─────────────────────┐
        │     MAXIMIZED       │
        │  fills plot area   │
        └─────────┬───────────┘
                  │
    double-click  │
                  ▼
        ┌─────────────────────┐
        │      NORMAL         │
        └─────────────────────┘

Rules:
- No modifier keys
- Other plots remain alive
- State does NOT affect data flow

---

## PLOT PRESENCE STATE (Visibility)

    ┌───────────────────┐
    │     ACTIVE        │
    │ visible in grid  │
    └─────────┬─────────┘
              │
        park  │
              ▼
    ┌───────────────────┐
    │     PARKED        │
    │ bottom bar       │
    │ still updating   │
    └─────────┬─────────┘
              │
        restore
              ▼
    ┌───────────────────┐
    │     ACTIVE        │
    └───────────────────┘

Rules:
- PARKED plots continue receiving data
- No state loss
- No confirmation dialogs

---

## OVERLAY (MULTI-SIGNAL) STATE

A plot may contain ONE OR MORE signals.

    ┌───────────────────┐
    │   EMPTY PLOT      │
    │ (no signals)     │
    └─────────┬─────────┘
              │
    probe /   │
    drop      │
              ▼
    ┌───────────────────┐
    │ SINGLE SIGNAL     │
    │ (default state)  │
    └─────────┬─────────┘
              │
 drag symbol  │
 onto plot    │
              ▼
    ┌───────────────────┐
    │ MULTI-SIGNAL      │
    │ (overlay mode)   │
    └─────────┬─────────┘
              │
  remove one  │
  signal      │
              ▼
    ┌───────────────────┐
    │ SINGLE SIGNAL     │
    └─────────┬─────────┘
              │
  remove last │
  signal      │
              ▼
    ┌───────────────────┐
    │   EMPTY PLOT      │
    └───────────────────┘

Overlay Rules:
- All signals share axes
- Axis changes affect all signals
- Each signal has independent:
  - color
  - legend entry
  - removal control

---

## INTERACTION MODE STATE (Mouse)

    ┌───────────────────┐
    │     POINTER       │  ← default
    └─────────┬─────────┘
              │
 select tool  │
              ▼
┌────────┬────────┬────────┬────────┐
│  PAN   │ ZOOM   │ ZOOM X │ ZOOM Y │
└────────┴────────┴────────┴────────┘
              │
action done   │
              ▼
    ┌───────────────────┐
    │     POINTER       │
    └───────────────────┘

Rules:
- All non-pointer modes are temporary
- Escape ALWAYS returns to POINTER
- Cursor icon must reflect mode

---

## GLOBAL INVARIANTS (MUST ALWAYS HOLD)

- Axis AUTO and PINNED are mutually exclusive
- Autoscale NEVER runs on a pinned axis
- Manual action ALWAYS pins
- No silent state transitions
- No modifier-key-only behaviors
- No dialog-based interactions

---

## Failure Conditions (Explicit Bugs)

- Axis changes without visible pin state
- Autoscale overriding manual scale
- Overlay signals desynchronizing axes
- Plot state unclear without interaction
- User unsure whether plot is live

If observed, the implementation is incorrect.

---

# PyProbe Plot Interaction — Reference Event Table (Authoritative)

This table defines how user/system events transition plot state.
If an event is not listed here, it must NOT change state.

---

## AXIS EVENTS (X and Y handled independently)

| Event | Preconditions | Effect |
|-----|--------------|--------|
| New data arrives | Axis = AUTO | Autoscale axis |
| New data arrives | Axis = PINNED | No scale change |
| Mouse zoom (any) | Any | Axis → PINNED |
| Mouse pan | Any | Axis → PINNED |
| In-place min edit | Any | Axis → PINNED |
| In-place max edit | Any | Axis → PINNED |
| Key `X` / `Y` | Axis = AUTO | Axis → PINNED |
| Key `X` / `Y` | Axis = PINNED | Axis → AUTO |
| Key `R` | Any | Axis → AUTO (autoscale resumes) |

---

## VIEW LAYOUT EVENTS

| Event | Current State | Next State |
|-----|--------------|-----------|
| Double-click plot | NORMAL | MAXIMIZED |
| Double-click plot | MAXIMIZED | NORMAL |

Rules:
- No modifier keys
- Data flow unaffected

---

## VISIBILITY EVENTS (PARKING)

| Event | Current State | Next State |
|-----|--------------|-----------|
| Park plot | ACTIVE | PARKED |
| Restore plot | PARKED | ACTIVE |

Rules:
- PARKED plots remain live
- No state reset

---

## OVERLAY / SIGNAL EVENTS

| Event | Signals Present | Result |
|-----|-----------------|--------|
| Probe symbol | 0 | Create SINGLE-SIGNAL plot |
| Drag symbol → plot | ≥1 | Add signal → MULTI-SIGNAL |
| Remove signal | >1 | Remain MULTI-SIGNAL |
| Remove signal | 1 | EMPTY plot |
| Remove last signal | 1 | EMPTY plot |

Rules:
- Axes are shared
- Axis state applies to all signals

---

## INTERACTION MODE EVENTS

| Event | Current Mode | Next Mode |
|-----|--------------|-----------|
| App start | — | POINTER |
| Select pan tool | POINTER | PAN |
| Select zoom tool | POINTER | ZOOM |
| Select zoom X | POINTER | ZOOM_X |
| Select zoom Y | POINTER | ZOOM_Y |
| Complete pan/zoom | Any | POINTER |
| Press Escape | Any | POINTER |

Rules:
- Non-pointer modes are temporary
- Cursor icon must match mode

---

## INVALID EVENTS (MUST BE IGNORED)

- Autoscale while axis is PINNED
- Axis sync across plots (not supported)
- Modifier-only mouse gestures
- Modal dialogs changing plot state

---

## HARD GUARANTEES

- Manual action always overrides automation
- No event causes silent state change
- All transitions must be visually reflected