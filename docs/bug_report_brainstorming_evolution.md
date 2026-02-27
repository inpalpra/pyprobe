# Evolution of the PyProbe "Scene Graph" Bug Reporting System

This document captures the rigorous brainstorming and architectural evolution of the PyProbe Bug Reporting feature. It serves as a historical record of how we transitioned from a basic "event logger" to a "hierarchical scene-graph snapshot" designed specifically for LLM diagnostics.

## Phase 1: The Foundation and the "Event Bubbling" Trap
**Initial State:** The reporter captured a description, a flat list of recorded steps, and a simple inventory of open files and probes.

**The Breaking Point:** Clicking a plot's legend label recorded a step, but clicking the "indicator line" (the color swatch) did not, even though the UI visually updated.
**Discovery:** Third-party libraries (like `pyqtgraph`) often have child widgets that "swallow" events. 
**Lesson:** AI Agents must use **Runtime Introspection** (reading library source at runtime) to identify where events are being accepted and use **Native Hooks** (connecting to the library's internal signals like `sigSampleClicked`) instead of fighting the framework with manual coordinate mapping.

## Phase 2: Signal-to-Noise and the "Data Deluge"
**The Problem:** Once we started recording manual view changes (pan/zoom) and marker movements, the report became unreadable. A single drag generated 100+ "Adjusted view" entries.

**The Pivot:**
1.  **Duplicate Suppression:** We implemented logic in `StepRecorder` to ignore consecutive identical descriptions.
2.  **Debouncing Continuous Input:** We realized that for diagnostic purposes, the *path* of a mouse drag is irrelevant; only the *intent* and the *final state* matter.
**Implementation:** Use a `QTimer` (e.g., 500ms) to wait for silence before recording a single "View adjusted" or "Marker moved" step.

## Phase 3: The "Homeless Probe" and Semantic Blind Spot
**The Realization:** We observed a report where a probe appeared in the "Baseline Probes" list but was nowhere to be found in the "Widgets" list. 
**The Cause:** `signal_q` was an **overlay** on a window primary-owned by `signal_i`. Our flat reporting structure only identified the primary owner.
**LLM Impact:** An LLM cannot reason about a UI it cannot "see." If the baseline says "Window w1: signal_i" and the steps say "Toggled signal_q," the LLM assumes a state-tracking bug.

## Phase 4: The 4-Tier Hierarchical "Scene Graph"
To solve the blind spot, we moved from an inventory list to a structured hierarchy. We decided to treat all data as fundamentally **Complex**, where Real-valued data is simply a subset with an imaginary part of zero.

### The Proposed Schema (The "App Object")

### Tier 1: Probes (Code Layer)
Maps symbols to physical source locations.
```yaml
Probes:
  p0: { symbol: signal_i, loc: "dsp_demo.py:72:26", dtype: float64, shape: (1024,) }
  p1: { symbol: signal_q, loc: "dsp_demo.py:72:27", dtype: float64, shape: (1024,) }
```

### Tier 2: Traces (Data Instance Layer)
The logical instances of data active in the session.
```yaml
Traces:
  tr0: { probe: p0, label: "signal_i" }
  tr1: { probe: p1, label: "signal_q" }
```

### Tier 3: Visual Items (The Aesthetics)
Inside the Widgets, we define the **Plots** (curves). This allows a single Trace (like a complex number) to split into two Visual Items (Real/Imag or Mag/Phase) with different colors.
```yaml
# Inside a Widget definition
plots:
  w1.p0: { source: tr0.real, color: "#00ffff", visible: true, markers: [m0] }
  w1.p1: { source: tr0.imag, color: "#ff00ff", visible: true }
```

### Tier 4: Annotations (Markers & Equations)
Markers are treated as high-detail objects in the Baseline (with coordinates) but debounced summaries in the Steps.
```yaml
Markers:
  m0: { type: "point", pos: [102.5, 0.8], label: "Peak", color: "#ffffff" }
```

## Phase 6: The "Final Mental Model" (The Complete App Object)

The final mental model treats the PyProbe session as a unified **App Object**. This object captures the entire state—from the code-level source to the visual layout—allowing an LLM to "reconstruct the scene" before processing any action steps.

### Comprehensive Baseline Example

```yaml
# Baseline State Snapshot (Single point-in-time)
App:
  Metadata:
    theme: "Tokyo Night"
    is_running: false
    layout_mode: "flow"

  Probes:
    p0: { symbol: signal_i, loc: "dsp_demo.py:72:26", dtype: float64, shape: (1024,) }
    p1: { symbol: signal_q, loc: "dsp_demo.py:72:27", dtype: float64, shape: (1024,) }
    p2: { symbol: rx_symbols, loc: "dsp_demo.py:72:30", dtype: complex128, shape: (512,) }

  Equations:
    eq0: { expression: "tr0 + tr1", label: "Composite", status: "valid" }

  Traces:
    tr0: { probe: p0, label: "signal_i" }
    tr1: { probe: p1, label: "signal_q" }
    tr2: { probe: p2, label: "rx_symbols" }
    tr3: { equation: eq0, label: "Summed" }

  Markers:
    m0: { type: "point", pos: [102.5, 0.8], label: "Peak", color: "#ffffff" }
    m1: { type: "delta", ref: "m0", pos: [150.2, 0.45], label: "Falloff", color: "#ffa500" }

  Layout:
    WatchPane:
      items:
        - { source: tr0.val, value: 0.852 }
        - { source: tr3.mag, value: 1.210 }
    
    Widgets:
      w0:
        position: 0
        lens: "Waveform"
        plots:
          w0.p0: { source: tr0.val, color: "#00ffff", visible: true, markers: ["m0", "m1"] }
          w0.p1: { source: tr1.val, color: "#ffff00", visible: true }
      
      w1:
        position: 1
        lens: "FFT Mag and Phase"
        plots:
          w1.p0: { source: tr2.fmag, color: "#00ffff", visible: true }
          w1.p1: { source: tr2.fphs, color: "#ff00ff", visible: true }
          w1.p2: { source: tr3.fmag, color: "#ffffff", visible: true } # Overlay of equation
```

---

## Conclusion: The "App Object" Philosophy
By providing this **High-Detail Baseline**, the **Steps (Audit Log)** are transformed from ambiguous descriptions into precise **State Deltas**.

**Action Recording Strategy:**
1.  **Semantic Overlays:** `Dragged tr2 from WatchPane to w0` (LLM knows `w0` now has an extra `plot` item).
2.  **Debounced View/Marker Updates:** `Adjusted marker m1 to [160.0, 0.3]` (LLM sees the final result).
3.  **Standardized Suffixes:** Suffixes (`.val`, `.real`, `.imag`, `.fmag`, `.fphs`) act as a protocol for the LLM to understand how the Plugin (Lens) is mapping Data to Visuals.

This prevents the model from having to "guess" the UI state from narrative text, creating a 1:1 bridge between user experience and AI diagnosis.
