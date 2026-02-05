# The PyProbe UX Constitution

These rules are non-negotiable.  
If a feature violates even one, it must be redesigned or removed.

---

## 1. Probing Is a Gesture, Not a Configuration
- Probing must be a single physical action.
- Hover → click → observe.
- No dialogs. No forms. No setup steps.

---

## 2. Every Action Must Acknowledge the User
- No silent failures.
- If an action has no effect, the UI must briefly explain *why*.
- Silence is treated as a bug.

---

## 3. Live Means Live
- Probes can be added or removed while code is running.
- New probes begin updating immediately (same or next frame).
- If something is not live, that state must be visible.

---

## 4. Code Is the Source of Truth
- Probe state must be visible in code before anywhere else.
- The user should be able to understand all probes by reading the code view alone.
- Watch lists and panels are secondary reflections.

---

## 5. Hover Predicts Click Exactly
- The symbol highlighted on hover is *exactly* what will be probed on click.
- Ambiguity at click time is forbidden.
- If a symbol cannot be probed, it must not highlight.

---

## 6. Every Probe Has an Obvious Lifecycle
- Armed → Live → Removed must be visually distinct.
- Adding and removing probes must feel final and deliberate.
- Users must never wonder if a probe is “still running somewhere”.

---

## 7. Liveness Is Always Discernible at a Glance
- Users must always be able to tell:
  - live
  - waiting
  - invalid
- This must require zero reading and zero interaction.

---

## 8. Structure Is Automatic, Override Is Optional
- Probes organize themselves by code context by default.
- Manual grouping is an override, not a requirement.
- The user should never start with chaos.

---

## 9. Visual Meaning Degrades Gracefully
- Color is a scarce resource.
- Too many colors must not destroy comprehension.
- Older or less relevant probes must visually recede.

---

## 10. Performance Cost Is Never Hidden
- If throttling or downsampling is active, it must be visible.
- Users must never guess whether the tool is “doing something expensive”.
- Transparency builds trust.

---

## 11. Discovery Beats Documentation
- Critical features must be discoverable through seeing, not reading.
- Disabled-but-visible UI is preferred over hidden capability.
- The user should stumble into power.

---

## 12. The Tool Must Disappear
- The user should think about signals, not PyProbe.
- Any moment of “how do I use this?” is a failure.
- If the tool becomes noticeable, it has already lost.

---

## Final Law

If a user has to stop thinking about the signal  
to manage the tool,  
the tool has failed.