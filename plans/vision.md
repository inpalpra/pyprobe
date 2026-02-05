# PyProbe — Intent, Pain, and Vision

---

## 1. What the user came to talk about

### Background
- User is RF / DSP engineer
- Long history with LabVIEW
- LabVIEW spoiled debugging:
  - click wire → see data
  - waveforms, spectra, constellations
  - probe sub-VIs easily
- Python DSP debugging feels painful:
  - print() useless
  - matplotlib static
  - pdb kills flow
  - notebooks don’t scale

---

### What you built (PyProbe today)

**What it is**
- Variable-probing debugger for Python DSP
- Runs Python script under `sys.settrace`
- GUI (PyQt6 + pyqtgraph)
- Live plots while code runs

**How it works**
- User runs: `python -m pyprobe script.py`
- Tracer intercepts variable assignments
- Sends values to GUI
- GUI auto-selects plot:
  - scalar → number
  - real array → waveform
  - complex → constellation

**Architecture (today)**
Python Script
|
sys.settrace
|
VariableTracer
|
IPC
|
GUI
|
Plots

**What you like**
- No code modification
- Live visualization
- DSP-friendly plots
- Zero-copy shared memory for big arrays
- Throttling to keep UI responsive
- Feels closer to LabVIEW than anything else in Python

---

### What you don’t like (pain points)

1. Probing by variable name
   - must type / copy-paste names
   - not natural
   - unlike clicking wires in LabVIEW

2. Weak across modules
   - works best for single file
   - helper files feel second-class
   - sub-VI probing missing

3. Rigid visualizations
   - complex array ≠ always constellation
   - sometimes want:
     - IQ waveform
     - spectrum
     - custom views
   - LabVIEW has Custom Probes
   - PyProbe needs user-defined probes

4. Variable names lose meaning
   - same name, different stages
   - location matters more than name
   - need “probe here, not just probe x”

5. UI does not scale
   - 20 probes = 20 plots = chaos
   - need grouping, tabs, structure

6. No offline probing
   - LabVIEW remembers wire values
   - can probe after execution ends
   - PyProbe currently loses everything when run ends

---

## 2. Vision for PyProbe

### Core vision (one sentence)
- PyProbe = **dataflow observability for Python DSP**
- Not a debugger
- Not an editor
- A live instrument panel

---

### Foundational shift (most important)

**From**
- “watch variable names”

**To**
- “observe data at source locations”

Like probing a wire, not a variable.

---

### Long-term user workflow (recommended)

**Editor**
- VS Code (or any editor)
- Write and edit code normally
- No PyProbe-specific code

**Runtime**
- Launch PyProbe separately
- PyProbe runs the script

**Interaction**
- PyProbe has:
  - file tree
  - read-only code viewer
- User clicks variable in PyProbe
- Probe appears
- Data flows live

**Mental model**
- VS Code = code
- PyProbe = signals

---

### Milestone roadmap (compressed)

#### Milestone 1 — Source-anchored probing
- Read-only code viewer in PyProbe
- Click variable → probe
- Probes work across modules
- Identity = (file, line, symbol)

#### Milestone 2 — Usability + extensibility
- Probe groups → tabs
- Custom probe plugins:
  - constellation
  - IQ
  - spectrum
  - class/object probes
- Right-click → change view

#### Milestone 3 — Offline probing
- Record execution
- Remember values per location
- Probe after run ends
- Scrub iterations / frames

---

### Recommended tech stack (stay close to today)

- Python
- sys.settrace (still core)
- PyQt6 (GUI)
- pyqtgraph (plots)
- multiprocessing + shared_memory
- Optional later:
  - mmap / sqlite for recording
  - numpy / scipy for probe plugins

No VS Code plugin required (optional later).

---

### Core architecture (target)

    ┌─────────────┐
    │  Code View  │  ← click here
    └──────┬──────┘
           |
    ProbeAnchor
    (file,line,sym)
           |
    ┌──────▼──────┐
    │   Runner    │
    └──────┬──────┘
           |
    ┌──────▼──────┐
    │  Tracer     │  sys.settrace
    └──────┬──────┘
           |
    ┌──────▼──────┐
    │   Data Bus  │  IPC / SHM
    └──────┬──────┘
           |
    ┌──────▼──────┐
    │  Probe UI   │
    └──────┬──────┘
           |
    ┌──────▼──────┐
    │ ProbePlugin │  ← stable API
    └─────────────┘

    ---

### Rock-solid foundations (must not change often)

**1. ProbeAnchor data model**
- file path
- line number
- symbol
- immutable identity

**2. Probe plugin API**
- accepts(value, context)
- render()
- update()
- plugins do not touch tracer internals

**3. Execution data contract**
- tracer emits values
- UI consumes values
- storage layer optional but clean

**4. Separation of concerns**
- Editor ≠ PyProbe
- UI ≠ tracer
- probe definition ≠ visualization

---

### Long-term feel (success criteria)

- Probing feels like clicking wires
- User thinks in signals, not variables
- Debugging is visual-first
- Python DSP debugging feels *native*, not bolted-on
- DSP engineers say:
  > “This feels like LabVIEW, but for Python”

---

### One-line philosophy

> Python stays textual.  
> PyProbe makes it visual.