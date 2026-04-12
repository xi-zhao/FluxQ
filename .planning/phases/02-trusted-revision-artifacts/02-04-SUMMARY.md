---
phase: 02-trusted-revision-artifacts
plan: 04
subsystem: runtime
tags: [replay-integrity, control-plane, workspace-history, legacy-compatibility]
requires:
  - phase: 02-trusted-revision-artifacts
    provides: trusted replay-integrity evaluation and revision-scoped manifest/history artifacts from earlier Phase 2 work
provides:
  - current-workspace import resolution pinned to immutable report and qspec history when a real revision exists
  - show/control-plane legacy fallback keyed to missing trusted digest evidence instead of schema_version heuristics
  - regressions covering mutable-alias tampering and legacy manifest synthesis semantics
affects: [runtime/imports, control-plane, show, replay-trust]
tech-stack:
  added: []
  patterns:
    - history-first current-workspace replay resolution
    - replay-integrity evidence as the legacy compatibility predicate
key-files:
  created:
    - .planning/phases/02-trusted-revision-artifacts/02-04-SUMMARY.md
  modified:
    - src/quantum_runtime/runtime/imports.py
    - src/quantum_runtime/runtime/control_plane.py
    - tests/test_runtime_imports.py
    - tests/test_cli_control_plane.py
key-decisions:
  - "Current-workspace replay now prefers immutable history artifacts over mutable latest/current aliases whenever the selected revision has persisted history."
  - "Legacy show fallback is now defined by absent trusted artifact-output digests, not by a missing schema_version field."
patterns-established:
  - "Use revision history as the source of truth for trusted current-workspace replay, falling back to aliases only for compatibility when history copies do not exist."
  - "Treat replay-integrity digest evidence as the control-plane trust signal for distinguishing trusted versus legacy runs."
requirements-completed: [RUNT-03]
duration: 10min
completed: 2026-04-12
---

# Phase 2 Plan 4: Trusted Current-Workspace Replay Pinned to Immutable History

**Current-workspace replay now reopens immutable revision history first, and `show` synthesizes legacy manifests only when trusted digest evidence is absent.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-12T13:08:10Z
- **Completed:** 2026-04-12T13:18:10Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added red regressions proving that mutating only `reports/latest.json` must not downgrade trusted current-workspace replay or `qrun show --json`.
- Updated current-workspace import resolution to reopen `reports/history/<revision>.json` and resolve the QSpec from immutable history before consulting mutable aliases.
- Replaced the stale `schema_version`-only legacy heuristic with replay-integrity digest evidence so genuine legacy reports still reopen without weakening trusted runs.

## Verification

- `uv run --python 3.11 --extra dev --extra qiskit pytest -q tests/test_runtime_imports.py tests/test_cli_control_plane.py`
- Result: `43 passed in 5.49s`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add regressions for current-workspace trust pinning and legacy detection** - `ad7b481` (`test`)
2. **Task 2: Pin current-workspace replay to immutable history and align legacy fallback with replay-integrity evidence** - `fcf3b55` (`fix`)

## Files Created/Modified

- `src/quantum_runtime/runtime/imports.py` - switched current-workspace resolution to prefer immutable history artifacts and captured the resolution source in provenance.
- `src/quantum_runtime/runtime/control_plane.py` - redefined legacy-compatible `show` fallback around missing trusted digest evidence.
- `tests/test_runtime_imports.py` - added alias-tampering coverage and updated current-workspace expectations to history-first replay.
- `tests/test_cli_control_plane.py` - added current-workspace `show` tamper coverage and updated legacy tests to remove digest evidence instead of `schema_version`.
- `.planning/phases/02-trusted-revision-artifacts/02-04-SUMMARY.md` - recorded execution outcomes and verification evidence for plan 02-04.

## Decisions Made

- Current-workspace trust is anchored to the immutable revision selected by `workspace.json`, not to the mutable `latest/current` aliases that may drift independently.
- A report is treated as legacy-compatible only when the trusted replay-integrity digest set is absent; keeping `schema_version` no longer blocks legacy synthesis.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The Phase 2 trust gap around mutable alias tampering is closed and backed by scoped regressions.
- `STATE.md` and `ROADMAP.md` were intentionally left untouched for the orchestrator to update after verification.

## Self-Check

PASSED

- Found `.planning/phases/02-trusted-revision-artifacts/02-04-SUMMARY.md` on disk.
- Verified task commits `ad7b481` and `fcf3b55` in `git log`.
- Stub scan over touched files found no placeholder markers.

---
*Phase: 02-trusted-revision-artifacts*
*Completed: 2026-04-12*
