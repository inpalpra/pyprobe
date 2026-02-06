# M2 Implementation Plans

This directory contains implementation plans for **M2: Plugin System (Lenses)** that can be worked on by multiple AI agents in parallel git worktrees.

## Plan Overview

| Plan | File | Focus | Complexity | Branch |
|------|------|-------|------------|--------|
| 0 | `00-plugin-abc.md` | ProbePlugin ABC & registry | S | `m2/plugin-abc` |
| 1 | `01-builtin-plugins.md` | Refactor existing plots to plugins | M | `m2/builtin-plugins` |
| 2 | `02-lens-ui.md` | Lens dropdown & context menu | M | `m2/lens-ui` |
| 3 | `03-integration.md` | Wire everything together | M | `m2/integration` |

## Execution Order

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Foundation                                             │
│   Plan 0 (must complete first, merge to main)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: Parallel Work (2 agents)                               │
│                                                                 │
│   Agent A: Plan 1 (Refactor plots → plugins)                    │
│   Agent B: Plan 2 (Lens UI components)                          │
│                                                                 │
│   Work in separate worktrees, no merge conflicts                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: Integration                                            │
│   Merge Phase 2 branches                                        │
│   Plan 3 (must run last)                                        │
└─────────────────────────────────────────────────────────────────┘
```

## Merge Conflict Prevention

| Plan | New Files | Modified Files | Conflict Risk |
|------|-----------|----------------|---------------|
| 0 | 2 | 0 | None |
| 1 | 5 | 1 (delete old) | Low |
| 2 | 1 | 1 (probe_panel) | Low |
| 3 | 0 | 2 (main_window, probe_panel) | Medium (run last) |

## UX Requirements Coverage

From M2 acceptance criteria in `plans/plan.md`:

| Requirement | Plan |
|-------------|------|
| View switching without re-probing | 3 (lens change preserves probe) |
| Switching views doesn't interrupt data | 1 (plugins share update contract) |
| Default view is reasonable | 0 (can_handle priority logic) |
| No right-click required for common ops | 2 (lens dropdown primary) |
| Lens switching is discoverable | 2 (visible dropdown in header) |
| Color consistent across lenses | 1 (plugins receive color, don't assign) |
| Probe identity preserved across views | 3 (registry tracks lens per anchor) |
| Unsupported views disabled, not hidden | 2 (dropdown shows all, disables incompatible) |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ ProbePanel (existing)                                           │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Header                                                      │ │
│ │  symbol @ file:line        [Waveform ▾]  ← LensDropdown     │ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │ Plugin Widget Area                                          │ │
│ │  ┌───────────────────────────────────────────────────────┐  │ │
│ │  │  WaveformPlugin / ConstellationPlugin / etc.          │  │ │
│ │  │  (implementing ProbePlugin ABC)                       │  │ │
│ │  └───────────────────────────────────────────────────────┘  │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ PluginRegistry (singleton)                                      │
│  - Discovers plugins at startup                                 │
│  - Matches (dtype, shape) → compatible plugins                  │
│  - Returns default plugin for each data type                    │
└─────────────────────────────────────────────────────────────────┘
```

## Full Implementation Details

For complete milestone spec, see: `plans/plan.md` (M2 section)

Each plan file contains structure, interfaces, and implementation notes.
