SYSTEM MODE: PYPROBE-SESSION-INIT

TASK:
Before any work, load project context to minimize wasted tokens.

MANDATORY STEPS:
0. Read `CONSTITUTION.md` completely
1. Read `.agent/README.md` completely
2. Scan LESSONS for relevant prior bugs AND process lessons
3. Check INVARIANTS before writing any code
4. Note PATTERNS for consistent style
5. Review DEBUG-FIRST-PATTERNS for complex bugs

AFTER READING:
- Confirm: "Context loaded. [N] lessons, [M] patterns indexed."
- Proceed with user request

DO NOT:
- Re-explore codebase if README has answer
- Repeat past mistakes documented in LESSONS
- Skip INVARIANTS check before Qt/callback code
- Make speculative fixes without tracing (see L10, L11)
- Debug IPC without logging both sides (see L12)

DEBUG-FIRST RULE (from L10, L11, L12):
For GUI state bugs or IPC issues:
1. Add state tracing BEFORE making code changes
2. Observe actual (State, Action) → (NewState) transitions
3. Log on BOTH sender AND receiver for IPC
4. Only hypothesize AFTER observing actual behavior

IF BUG FIXED THIS SESSION:
- Remind user: "Run @[prompts/END.md] before closing"
- END.md requires BOTH code bug lessons AND process/behavioral lessons
