============================================================
1. TOGGLE-BASED ACTIONS (IDEMPOTENT / SYMMETRIC)
============================================================

EXAMPLES:

FOCUS_WIDGET + M
    → Toggle maximize / restore

FOCUS_WIDGET + P
    → Toggle park / unpark   (if focusable)
    → OR if parked widgets cannot receive focus:
         - P only parks
         - Unpark must be triggered elsewhere

FOCUS_WIDGET + G
    → Toggle grid

FOCUS_WIDGET + H
    → Toggle hover display

FOCUS_WIDGET + L
    → Toggle legend visibility

FOCUS_WIDGET + 1
    → Toggle TR1 visibility

FOCUS_WIDGET + 2
    → Toggle TR3 visibility


============================================================
2. CLEAN MINIMAL SHORTCUT SET (RECOMMENDED)
============================================================

Widget-Level (requires focus):

M        → Toggle maximize
P        → Park widget
R        → Reset / Auto scale
Z        → Zoom tool
H        → Pan tool (Hand)
ESC      → Standard Mouse tool
X        → Close Widget 

Global:

TAB      → Cycle widgets


============================================================
3. IMPORTANT DESIGN PRINCIPLE
============================================================

Shortcut must satisfy:

1. Reachable state
2. Low cognitive load
3. No symmetry obsession
4. No focus paradox

If a shortcut requires focusing something that is
structurally difficult to focus, the shortcut is invalid.

============================================================
4. CLEAN RULE FOR TOGGLES
============================================================

If action is a binary view-state:
    → Single key toggle (press again to revert)

