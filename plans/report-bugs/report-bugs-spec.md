User Story: In-App “Report Bug” Feature with Reproducible Step Recording

Title:
As a PyProbe user, I want to report bugs from within the application and automatically record reproducible steps (including my interactions, loaded traces, and open Python files), so that developers can reliably reproduce and fix issues.

---

Primary User Story

As a user,
When I encounter unexpected behavior in PyProbe,
I want to click a “Report Bug” button and optionally enable a “Record Steps” mode,
So that I can generate a structured, developer-ready bug report containing:
- Steps to reproduce (automatically recorded)
- Current session state
- List and contents of open/probed Python files
- Loaded traces and configuration
- Environment information

---

User Flow

1. User clicks: Help → Report Bug

2. A “Report Bug” dialog opens with:
   - Text field: "Describe what went wrong"
   - Button: "Start Recording Steps"
   - Button: "Stop Recording"
   - Button: "Generate Report"
   - Checkbox: "Include open file contents"
   - Checkbox: "Include logs"
   - Checkbox: "Include system info"

3. If user clicks “Start Recording Steps”:
   - Application immediately captures a “Baseline State Snapshot”
     (open files, probed traces, active equations, graph widgets).
   - Application enters “Recording Mode”.
   - A small floating red indicator appears: ● Recording Steps
   - All relevant UI actions are recorded in structured format
   - All subsequent steps are treated as mutations relative to the baseline snapshot.
   
4. User reproduces the bug naturally.

5. User clicks “Stop Recording”.

6. User clicks “Generate Report”.

7. The app generates:
   - A structured plaintext bug report
   - Option to:
     - Copy to clipboard
     - Save to file
     - Open pre-filled GitHub issue page
     - Send to Claude/LLM

---

Functional Requirements

1. Step Recording System

The system must record user actions in structured chronological order, including:

- Menu actions (View → Equation Editor)
- Button clicks (Plot eq0)
- Widget open/close events
- Trace probing actions
- Equation edits
- File loads
- Configuration loads
- Keyboard shortcuts (e.g., pressing P)
- Docking/undocking actions
- Graph creation/destruction

Each step should be recorded in human-readable form, e.g.:

Step 1: Launched application with examples/dsp_demo.py
Step 2: Opened Equation Editor from View menu
Step 3: Added Equation (eq0)
Step 4: Set eq0 = np.power(tr0, 2)
Step 5: Clicked Plot for eq0
Step 6: Closed graph widget “eq0”
Step 7: Clicked Plot for eq0 again

Internally, steps should also be structured (JSON-like event objects).

---

2. Session State Capture
Baseline Snapshot Requirement:
The full session state must be captured at the moment “Start Recording Steps” is clicked.
This baseline snapshot represents the exact starting condition of the application before
any reproduction steps occur.

The bug report must include:

A. Open Python Files
- Full file path
- Whether file was probed
- Whether file was executed
- Whether file is modified/unsaved
- Optional: Full file contents (if user allows)

Format:

Open Files:
- examples/dsp_demo.py
  - Probed: Yes
  - Executed: Yes
  - Unsaved changes: No
  - Contents:
    ```python
    ...
    ```

B. Probed Traces
- Trace name
- Source file
- Shape
- Sample rate (if applicable)
- Metadata

C. Active Equations
- Equation ID
- Expression
- Status
- Whether plotted
- Target widget (if any)

D. Graph Widgets
- Widget ID
- What is plotted
- Dock state
- Visibility state

E. Loaded Configuration
- Config file path
- Serialized config snapshot (optional)

F. Optional Screenshot
- If user enables “Include Screenshot”:
  - Capture screenshot of main application window at the moment “Generate Report” is clicked.
  - Save as attached PNG file (not embedded base64 in plaintext report).

---

3. Environment Snapshot

Include:

- PyProbe version
- Git commit hash (if dev mode)
- Python version
- Platform (macOS/Linux/Windows)
- Qt version
- Installed plugin list
- Relevant environment variables (optional)
- Virtualenv path

---

4. Log Capture

Optional inclusion of:

- Last N lines of application log
- Tracebacks (if any)
- Warning messages
- Silent failures (if detectable)

---

5. Output Format

The generated report should be:

- Structured plaintext (LLM-friendly)
- Copy-paste ready
- Deterministic format
- Clearly separated sections

Example Structure:

------------------------------------------------------------
PYPROBE BUG REPORT
------------------------------------------------------------

Summary:
<User description>

Steps to Reproduce:
1.
2.
3.

Expected Behavior:

Actual Behavior:

Session State:
  Open Files:
  Probed Traces:
  Equations:
  Graph Widgets:

Environment:
  PyProbe Version:
  Python:
  OS:

Logs:
  ...

------------------------------------------------------------

Path Sanitization Requirement:
All absolute file paths must be sanitized before generating the report.
User-identifiable home directories must be replaced with:
  <USER_HOME>

Examples:
  /Users/prabhatpal/repos/pyprobe → <USER_HOME>/repos/pyprobe
  C:\Users\JaneDoe\Documents → <USER_HOME>\Documents

Sanitization must apply to:
- Open file lists
- Trace source paths
- Log entries
- Tracebacks

---

Non-Functional Requirements

1. Zero performance impact when not recording.
2. Recording must be lightweight and event-driven.
3. No sensitive data should be included without explicit consent.
4. File contents must be opt-in.
5. Large files should be truncated with size warning.
6. Report generation must not crash even if system state is partially corrupted.

---

Advanced Features (Future Milestones)

1. “Replay Mode”
   - Developers can replay recorded steps inside a test harness.

2. Deterministic Event Log
   - Store as structured JSON alongside plaintext report.

3. Auto-Minimal Repro Extractor
   - Attempt to generate minimal script that reproduces issue.

4. Session Snapshot Archive
   - Save compressed reproducible project state.

5. LLM Optimization Mode
   - Generate a second version of the report specifically optimized for AI coding agent like Claude/Codex/Copilot/Gemini consumption.

---

Acceptance Criteria

- User can start and stop step recording.
- Recorded steps are accurate and human-readable.
- Closing and reopening widgets is correctly captured.
- Open Python file list and contents are correctly captured (when enabled).
- Report can be copied in one click.
- Feature does not interfere with normal application use.
- Works for both simple UI bugs and complex state bugs.

---

Definition of Done

- Manual testing confirms accurate step capture.
- Automated test simulates a few UI events and validates log.
- Report generated for known bug (e.g., equation re-plot bug) contains sufficient detail for developer reproduction.
- No crashes when recording mode is active.

Implementation Guidance (Minimal Scope):

- Use an application-level event interception mechanism (e.g., Qt event filter)
  to record relevant UI actions without invasive refactoring.
- Recording may remain in-memory for v1 (no crash-recovery streaming required).
- Baseline snapshot + mutation steps must be sufficient to reproduce most state bugs.
