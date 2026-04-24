---
phase: 03-concurrent-workspace-safety
plan: 01
subsystem: infra
tags: [workspace, locking, atomic-write, pytest]
requires:
  - phase: 02-trusted-revision-artifacts
    provides: revisioned workspace manifests and replayable runtime artifacts
provides:
  - workspace-scoped writer lease under `.quantum/.workspace.lock`
  - atomic text promotion for bootstrap files and `workspace.json`
  - concurrency regressions for bootstrap conflicts and interrupted temp writes
affects: [03-02, 03-03, 03-04, workspace]
tech-stack:
  added: []
  patterns: [exclusive file lease, same-directory temp replace, reload-under-lock revision bump]
key-files:
  created: [src/quantum_runtime/workspace/locking.py, tests/test_workspace_locking.py]
  modified: [src/quantum_runtime/workspace/__init__.py, src/quantum_runtime/workspace/manager.py, src/quantum_runtime/workspace/manifest.py, tests/test_cli_init.py]
key-decisions:
  - "Use a filesystem lease at `.quantum/.workspace.lock` with JSON holder metadata instead of in-memory coordination."
  - "Keep `WorkspaceHandle.reserve_revision()` stable for callers, but reacquire the lease and reload the manifest under lock before bumping."
  - "Use one same-directory temp-write helper for manifest and bootstrap seed files so interrupted writes never replace committed state."
patterns-established:
  - "Workspace mutation starts with `acquire_workspace_lock(root)` and fails fast with `WorkspaceLockConflict`."
  - "Mutable workspace files are promoted with temp-file write, flush, fsync, and `os.replace`."
  - "Revision reservation reads the latest persisted manifest while the lease is held."
requirements-completed: [RUNT-02]
duration: 3 min
completed: 2026-04-12
---

# Phase 03 Plan 01: Workspace Lease Summary

**Workspace-scoped writer lease with atomic bootstrap and manifest promotion for shared `.quantum` state**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-12T15:02:34Z
- **Completed:** 2026-04-12T15:05:46Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added `WorkspaceLock`, `WorkspaceLockConflict`, and `acquire_workspace_lock()` for exclusive workspace writers with holder metadata.
- Moved `workspace.json`, `qrun.toml`, `events.jsonl`, and `trace/events.ndjson` seeding onto a same-directory temp write plus atomic replace path.
- Guarded `WorkspaceManager.load_or_init()` and `WorkspaceHandle.reserve_revision()` with the workspace lease and regression-tested conflict and interrupted-write behavior.

## Task Commits

Each task was committed atomically:

1. **Task 1: Lock down concurrent bootstrap and mutation behavior with failing tests** - `4c2d818` (`test`)
2. **Task 2: Implement the workspace lock lease and atomic bootstrap-write helpers** - `112bc88` (`feat`)

**Plan metadata:** Skipped by design. The orchestrator owns post-verification `STATE.md` and `ROADMAP.md` writes for this run.

## Files Created/Modified

- `src/quantum_runtime/workspace/locking.py` - filesystem lease acquisition, holder metadata, and conflict object
- `src/quantum_runtime/workspace/manifest.py` - atomic text write helper and atomic manifest persistence
- `src/quantum_runtime/workspace/manager.py` - lock-guarded bootstrap, atomic seed writes, reload-under-lock revision reservation, and corrected `created` calculation
- `src/quantum_runtime/workspace/__init__.py` - public workspace exports for the new lock and atomic write helpers
- `tests/test_workspace_locking.py` - workspace-layer lock, conflict, and interrupted-write regression coverage
- `tests/test_cli_init.py` - CLI bootstrap conflict/idempotency and interrupted-temp-file coverage

## Decisions Made

- Used a `.workspace.lock` lease file inside the workspace root so competing processes coordinate through the filesystem boundary they already share.
- Kept the existing `WorkspaceHandle.reserve_revision()` call shape to avoid widening this plan into executor-facing refactors.
- Left CLI conflict envelope normalization to Phase `03-02`; this plan only guarantees stable workspace-layer conflict metadata plus a detectable CLI conflict code/path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `InitResult.created` to reflect real bootstrap creation**
- **Found during:** Task 2
- **Issue:** `WorkspaceManager.init_workspace()` reported `created=True` after any successful load because it checked filesystem existence after bootstrap/load work had already run.
- **Fix:** Compute manifest existence before `load_or_init()` and return that pre-bootstrap result in `InitResult.created`.
- **Files modified:** `src/quantum_runtime/workspace/manager.py`
- **Verification:** `PYTHONPATH=src ./.venv/bin/python -m pytest tests/test_workspace_locking.py tests/test_workspace_manager.py tests/test_cli_init.py -q`
- **Committed in:** `112bc88`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The fix tightened bootstrap truthfulness without expanding scope beyond the owned workspace layer.

## Issues Encountered

- `qrun init --json` still surfaces lock conflicts through Typer's default traceback formatting because `src/quantum_runtime/cli.py` is outside this plan's write scope. The tests therefore lock the CLI contract to a stable conflict code and lock path only. Phase `03-02` should wrap this workspace conflict in a first-class machine-readable CLI payload.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `WorkspaceLock`, `WorkspaceLockConflict`, `acquire_workspace_lock`, and `atomic_write_text` are available for the CLI/runtime conflict surfaces in Phase `03-02` and the broader mutation graph in Phase `03-03`.
- Bootstrap and manifest writes now preserve last-known-good state during interrupted temp-file promotion.
- Remaining follow-up: normalize workspace conflict reporting at the CLI layer without relying on traceback output.

## Self-Check: PASSED

- Verified file exists: `src/quantum_runtime/workspace/locking.py`
- Verified commits exist: `4c2d818`, `112bc88`

---
*Phase: 03-concurrent-workspace-safety*
*Completed: 2026-04-12*
