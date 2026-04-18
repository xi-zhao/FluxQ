---
phase: 03-concurrent-workspace-safety
plan: 03
subsystem: infra
tags: [workspace, exec, provenance, atomic-write, pytest]
requires:
  - phase: 03-concurrent-workspace-safety
    provides: workspace lease metadata, atomic write helpers, and CLI workspace-safety error contracts from Plans 01-02
provides:
  - lease-guarded exec revision reservation and interrupted-commit rollback of `workspace.json`
  - history-first exec persistence with deferred current/latest alias promotion
  - revision-scoped event snapshots and conflict-safe recovery checks for report/manifest commit surfaces
affects: [03-04, workspace, exec, export, pack]
tech-stack:
  added: []
  patterns: [history-first artifact persistence, atomic alias promotion by copy, staged event-log commit]
key-files:
  created: []
  modified: [src/quantum_runtime/runtime/executor.py, src/quantum_runtime/workspace/manifest.py, src/quantum_runtime/workspace/manager.py, src/quantum_runtime/workspace/__init__.py, src/quantum_runtime/reporters/writer.py, src/quantum_runtime/runtime/run_manifest.py]
key-decisions:
  - "Hold the workspace lease across exec so a competing writer fails before revision reservation or artifact promotion."
  - "Write revision history artifacts first and only promote current/latest aliases after report and manifest history exist."
  - "Stage exec events in cache, snapshot them per revision, and append to authoritative event streams only after manifest history is written."
patterns-established:
  - "Exec writes immutable history roots first, then promotes aliases via `atomic_copy_file()`."
  - "Interrupted report/manifest temp files are treated as recovery blockers before a new exec can reserve a revision."
  - "Failed exec commits restore `workspace.json.current_revision` to the previous authoritative revision."
requirements-completed: [RUNT-02]
duration: 18 min
completed: 2026-04-12
---

# Phase 03 Plan 03: Exec Workspace Safety Summary

**Lease-guarded exec commits with history-first artifact staging, coherent alias promotion, and revision-scoped event snapshots**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-12T15:26:00Z
- **Completed:** 2026-04-12T15:44:47Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Made `qrun exec` hold the workspace lease from revision reservation through final promotion so concurrent execution now yields one winner and one structured conflict.
- Reworked exec persistence to write revision history first, defer `current`/`latest` alias promotion, and leave the prior authoritative revision readable when commit-time failures occur.
- Added reusable atomic copy and interrupted-temp detection helpers that Wave 4 can reuse for compare, benchmark, doctor, baseline, export, and pack writes.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add end-to-end tests for concurrent exec and interrupted commit safety** - `188f8c3` (`test`)
2. **Tasks 2-3: Guard exec commit flow, staged events, and atomic alias promotion** - `cf636c6` (`feat`)

**Plan metadata:** Summary-only closeout by design. `STATE.md` and `ROADMAP.md` remain orchestrator-owned for the phase-level completion pass.

## Files Created/Modified

- `src/quantum_runtime/runtime/executor.py` - rebuilt the exec source module and moved it to a lease-guarded, history-first commit flow with staged event logs and rollback-safe revision handling
- `src/quantum_runtime/workspace/manifest.py` - added `atomic_copy_file()` and shared interrupted-temp discovery for alias promotion and recovery checks
- `src/quantum_runtime/workspace/manager.py` - allowed `reserve_revision()` to run under an already-held lease
- `src/quantum_runtime/workspace/__init__.py` - exported the new workspace mutation primitives for downstream runtime writers
- `src/quantum_runtime/reporters/writer.py` - added history-only report writes plus interrupted-temp guarding for `reports/latest.json`
- `src/quantum_runtime/runtime/run_manifest.py` - added history-only manifest writes plus shared interrupted-temp guarding for `manifests/latest.json`

## Decisions Made

- Used history paths as the canonical exec output roots for Qiskit, QASM, diagrams, reports, manifests, and event snapshots, then promoted aliases from those immutable artifacts.
- Treated `reports/latest.json` and `manifests/latest.json` temp leftovers as the minimal recovery gate for this wave so failed commits stop before reserving a new authoritative run.
- Restored `workspace.json.current_revision` on exec commit failure so workspace control-plane state does not drift ahead of the last readable run.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Recreated the tracked `runtime/executor.py` source file from the repo state before applying Wave 3 changes**
- **Found during:** Task 2
- **Issue:** The working tree no longer had `src/quantum_runtime/runtime/executor.py`, and test imports were only succeeding because Python was loading stale bytecode from `__pycache__`.
- **Fix:** Restored the source module as part of the planned exec hardening work, then applied the new lease-guarded commit flow on top of that recovered source.
- **Files modified:** `src/quantum_runtime/runtime/executor.py`
- **Verification:** `python -m py_compile src/quantum_runtime/runtime/executor.py`
- **Committed in:** `cf636c6`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The deviation was required to execute the planned work safely. No scope was added beyond the owned exec mutation path.

## Issues Encountered

- The concurrent exec regression monkeypatch forced `write_diagrams()` to return current-alias paths, so the first green attempt still reported diagram paths outside history. The exec path now normalizes diagram outputs back into `artifacts/history/<revision>/figures/...` before report generation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 4 can reuse `atomic_copy_file()`, `pending_atomic_write_files()`, and the `promote_latest=False` history-first pattern for the remaining non-exec workspace writers.
- The exec path now proves the target safety contract: one winner under contention, no current/latest drift on manifest-write failure, and revision-scoped event snapshots tied to the winning run.
- Remaining follow-up: extend the same lease and atomic-promotion discipline to compare, benchmark, doctor, baseline, export, and pack persistence.

## Self-Check: PASSED

- Verified file exists: `src/quantum_runtime/runtime/executor.py`
- Verified command passes: `PYTHONPATH=src ./.venv/bin/python -m pytest tests/test_runtime_workspace_safety.py tests/test_cli_exec.py -q`
- Verified commits exist: `188f8c3`, `cf636c6`

---
*Phase: 03-concurrent-workspace-safety*
*Completed: 2026-04-12*
