Please re-evaluate M1 (Source-Anchored Probing) with the following *brutal UX teardown in mind*. Assume all planned M1 features work correctly. These are the things that will STILL feel annoying unless explicitly addressed. Update the plan to eliminate or mitigate each item.

---

## Brutal M1 UX Teardown — What Will Still Be Annoying

### 1. Silent “Why Didn’t That Probe?” Failures
- Clicking a symbol and seeing *nothing* feels like a bug.
- Silence is unacceptable even if behavior is technically correct.

**Required mitigation:**
- On invalid probe clicks, provide brief micro-feedback (pulse, dim highlight, or one-time tooltip).
- No persistent warnings. Just acknowledgement.

---

### 2. “Is This Live or Frozen?” Ambiguity
- A plot that isn’t updating creates doubt.
- Users can’t tell if the issue is code, throttle, pause, or probe failure.

**Required mitigation:**
- Each probe must have a single-glance liveness indicator:
  - live / armed / invalid
- Purely visual. No text.

---

### 3. First-Hit Latency Feels Like Failure
- Probes that appear but show no data initially feel broken.
- Users don’t know if the code path has executed yet.

**Required mitigation:**
- Probes enter an explicit “armed but waiting” state.
- Placeholder visuals until first data arrives.

---

### 4. Cursor Trust & Click Precision Anxiety
- Ambiguous hover targets slow users down.
- Users must not guess what will be probed.

**Required mitigation:**
- On hover, highlight the *exact* symbol that will be probed on click.
- Click behavior must never differ from hover indication.

---

### 5. Color Overload Degrades Meaning
- Rapid probing assigns many colors with diminishing cognitive value.
- Users quickly lose track of which signal is which.

**Required mitigation:**
- Enforce a limited active color palette.
- De-emphasize older probes visually.
- Preserve color consistency, not novelty.

---

### 6. Probe Removal Lacks Finality
- Removing a probe must feel decisive.
- Users worry probes may still be running invisibly.

**Required mitigation:**
- Removal must include a clear visual “off” moment (fade, collapse, pulse).
- No ambiguity about lifecycle termination.

---

### 7. Probe Locations Are Easy to Miss While Scrolling
- Gutter icons alone are too passive in large files.
- Users lose spatial awareness of probes.

**Required mitigation:**
- Add subtle scrollbar/minimap markers for probe locations.
- Extremely low visual weight, color-matched.

---

### 8. Probe Identity Is Not Verbally Nameable
- Users ask: “Which probe is this again?”
- Color and position are insufficient identifiers.

**Required mitigation:**
- Every probe panel must show a quiet identity label:
  - `symbol @ file:line`
- Always visible. Never hidden behind interaction.

---

### 9. Performance Cost Is Opaque
- Users can’t tell when downsampling or throttling is active.
- This causes self-censorship or paranoia.

**Required mitigation:**
- Subtle indicators when:
  - throttling is active
  - downsampling is occurring
- Informative, not alarming.

---

### 10. The Tool Still Feels Like a Tool
- Any moment where the user thinks:
  “What does PyProbe want me to do?”
  is a failure.

**Required mitigation:**
- Remove or hide anything that smells like configuration.
- Interactions must feel inevitable, not chosen.
- Probing must feel like touching a signal, not operating software.

---

## Acceptance Rule

M1 is not complete until:
- No action results in silent uncertainty.
- No probe state is ambiguous.
- The user never has to stop thinking about the signal to manage the tool.

Revise M1 to explicitly address these UX failure modes.