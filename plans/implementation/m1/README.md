# M1 Implementation Plans

This directory contains implementation plans for **M1: Source-Anchored Probing** that can be worked on by multiple AI agents in parallel git worktrees.

## Plan Overview

| Plan | File | Focus | Complexity | Branch |
|------|------|-------|------------|--------|
| 0 | `00-foundation.md` | Shared interfaces & stubs | S | `m1/foundation` |
| 1 | `01-ast-locator.md` | AST analysis module | M | `m1/ast-locator` |
| 2 | `02-code-viewer.md` | Code viewer widget | L | `m1/code-viewer` |
| 3 | `03-file-watcher.md` | File watcher & anchor mapping | M | `m1/file-watcher` |
| 4 | `04-tracer-refactor.md` | Tracer modifications | M | `m1/tracer-refactor` |
| 5 | `05-visual-polish.md` | UX polish & liveness | L | `m1/visual-polish` |
| 6 | `06-integration.md` | Main window integration | M | `m1/integration` |

## Execution Order

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Foundation                                             │
│   Plan 0 (must complete first, merge to main)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: Parallel Work (4 agents)                               │
│                                                                 │
│   Agent A: Plan 1 → Plan 2 (AST + Code Viewer)                  │
│   Agent B: Plan 3 (File Watcher)                                │
│   Agent C: Plan 4 (Tracer Refactor)                             │
│   Agent D: Plan 5 (Visual Polish)                               │
│                                                                 │
│   All work in separate worktrees, no merge conflicts            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: Integration                                            │
│   Merge all Phase 2 branches                                    │
│   Plan 6 (must run last)                                        │
└─────────────────────────────────────────────────────────────────┘
```

## Merge Conflict Prevention

| Plan | New Files | Modified Files | Conflict Risk |
|------|-----------|----------------|---------------|
| 0 | 4 | 1 (append) | Low |
| 1 | 3 | 0 | None |
| 2 | 3 | 0 | None |
| 3 | 2 | 0 | None |
| 4 | 1 | 2 (isolated) | Medium |
| 5 | 2 | 3 (stubs) | Medium |
| 6 | 0 | 1 | High (run last) |

## UX Requirements Coverage

The plans collectively address all brutal teardown requirements:

| Requirement | Plan |
|-------------|------|
| #1 Silent failures | 5 (pulse animation) |
| #2 Live/frozen ambiguity | 5 (liveness indicators) |
| #3 First-hit latency | 5 (armed state) |
| #4 Cursor trust | 2 (hover = click) |
| #5 Color overload | 5 (limited palette) |
| #6 Removal finality | 5 (fade animation) |
| #7 Scroll probe visibility | 2 (scrollbar markers) |
| #8 Identity naming | 5 (identity labels) |
| #9 Performance opacity | 5 (throttle indicator) |
| #10 Tool feels like tool | All (minimal config) |

## Full Implementation Details

For complete code implementations, see the main plan file:
`/Users/ppal/.claude/plans/noble-foraging-cook.md`

Each plan file here contains the structure and key implementation notes.
The full code for each class/function is in the main plan file.
