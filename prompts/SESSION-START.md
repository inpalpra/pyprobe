SYSTEM MODE: PYPROBE-SESSION-INIT

TASK:
Before any work, load project context to minimize wasted tokens.

MANDATORY STEPS:
1. Read `.agent/README.md` completely
2. Scan LESSONS for relevant prior bugs
3. Check INVARIANTS before writing any code
4. Note PATTERNS for consistent style

AFTER READING:
- Confirm: "Context loaded. [N] lessons, [M] patterns indexed."
- Proceed with user request

DO NOT:
- Re-explore codebase if README has answer
- Repeat past mistakes documented in LESSONS
- Skip INVARIANTS check before Qt/callback code

IF BUG FIXED THIS SESSION:
- Remind user: "Run @[prompts/UPDATE-LESSONS.md] before closing"
