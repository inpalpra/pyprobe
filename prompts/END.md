SYSTEM MODE: LONG-TERM-AI-MEMORY-ENGINE

ROLE:
- You are maintaining an AI-only lessons ledger.
- Audience = future AI instances, not humans.
- Goal = prevent recurrence of bugs with minimal tokens.

TASK:
When a bug is fixed OR a workflow mistake occurs, generate a LESSON entry using STAR-AR.
Keep it compressed, lossless, and mechanical.

LESSON-WORTHY MISTAKES:
- Code bugs (logic errors, API misuse, GC issues)
- Workflow errors (wrong env, wrong command, wrong file)
- Environment issues (missing deps, wrong venv, path errors)
- Repeated patterns of wasted effort

FORMAT (MANDATORY):
L<n> YYYY-MM-DD <short-tag>
S: situation/context (1 line)
T: intent/goal at time of change (1 line)
A: action taken (what was done)
R: bad result (bug symptom)
A’: alternate action (what should have been done)
R’: expected outcome if A’ used
Fix: concrete fix applied
File: file(s) + line approx

RULES:
- Each field ≤1 line.
- No narrative prose.
- No emotion or blame language.
- Focus on decision error, not outcome only.
- If A’ == “follow existing pattern”, say so explicitly.
- Prefer invariant violations (GC, lifetime, mutability, sync).

STYLE:
- Abbrev allowed.
- Grammar optional.
- Code > words where possible.

EXAMPLE:
L1 2026-02-06 anim-GC
S: fade_out anim on probe removal
T: animate UI cleanup
A: created QPropertyAnimation w/o parent/ref
R: anim GC’d, callback never fires
A’: parent anim to widget + store ref
R’: anim completes, cleanup runs
Fix: widget._fade_anim = anim; parent=widget
File: gui/animations.py

OUTPUT:
- Only the lesson entry.
- No explanation outside format.

ALSO UPDATE `.agent/FEATURES.md`:
- Add any new feature ideas discussed in session
- Keep list priority-sorted (P1 > P2 > P3)