---
phase: 03-concurrent-workspace-safety
plan: 04
subsystem: infra
tags: [workspace, compare, bench, doctor, export, pack, baseline, pytest]
requires:
  - phase: 03-concurrent-workspace-safety
    provides: exec-side lease, history-first alias promotion, and workspace-safety CLI envelopes from Plans 01-03
provides:
  - lock-scoped persistence for compare, benchmark, doctor, baseline, export, and pack
  - recovery-required guards for interrupted temp files across non-exec workspace writers
  - runtime pack staging and report-aware backfill for missing intent/plan history artifacts
affects: [workspace, compare, bench, doctor, export, pack, baseline]
tech-stack:
  added: []
  patterns: [lock-only-around-mutation, current-alias validation, staged pack directory promotion]
key-files:
  created: []
  modified: [src/quantum_runtime/cli.py, src/quantum_runtime/diagnostics/benchmark.py, src/quantum_runtime/runtime/compare.py, src/quantum_runtime/runtime/doctor.py, src/quantum_runtime/runtime/export.py, src/quantum_runtime/runtime/pack.py, src/quantum_runtime/workspace/baseline.py, src/quantum_runtime/workspace/__init__.py, tests/test_cli_compare.py, tests/test_cli_bench.py, tests/test_cli_doctor.py, tests/test_cli_baseline.py, tests/test_cli_export.py, tests/test_cli_runtime_gap.py]
key-decisions:
  - "Keep non-exec commands lock-free during pure compute/import work and acquire the workspace lease only for the final mutation section."
  - "Make export validate `reports/latest.json` against `specs/current.json` for `workspace_current` inputs so tampered current aliases fail closed."
  - "Stage packs in `.quantum/packs/.<revision>.tmp` and backfill missing intent/plan history from the revision report rather than the stricter revision resolver."
patterns-established:
  - "Non-exec latest/history JSON writers use `pending_atomic_write_files()` plus `atomic_write_text()` under `acquire_workspace_lock()`."
  - "CLI mutators normalize workspace lock failures and interrupted-write leftovers through `_handle_workspace_safety_error()`."
  - "Pack backfills synthesize `intent.json` and `plan.json` from the revision report when history files are missing."
requirements-completed: [RUNT-02]
duration: 14 min
completed: 2026-04-12
---

# Phase 03 Plan 04: Remaining Writer Safety Summary

**Lock-guarded compare, benchmark, doctor, baseline, export, and pack persistence with recovery checks for interrupted writes**

## Performance

- **Duration:** 14 min
- **Started:** 2026-04-12T15:45:00Z
- **Completed:** 2026-04-12T15:59:03Z
- **Tasks:** 3
- **Files modified:** 15

## Accomplishments

- Added failing-first workspace-safety regressions for every remaining non-exec writer: compare, benchmark, doctor, baseline, export, and pack.
- Moved non-exec persistence onto the same lease and interrupted-temp contract as exec, with atomic JSON writes and structured conflict/recovery surfaces in the CLI.
- Hardened `qrun export` current-workspace validation and `qrun pack` history backfills so both commands fail closed instead of silently trusting stale or partial state.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add CLI regressions for remaining non-exec workspace writers** - `cfb1e9a` (`test`)
2. **Tasks 2-3: Guard compare, benchmark, doctor, baseline, export, and pack mutations** - `8c9c385` (`feat`)

**Plan metadata:** Summary-only closeout by design. Phase-level `STATE.md` and `ROADMAP.md` updates remain for the orchestrator after final verification.

## Files Created/Modified

- `src/quantum_runtime/runtime/compare.py` - guarded compare persistence with workspace lease, interrupted-temp detection, and atomic latest/history writes
- `src/quantum_runtime/diagnostics/benchmark.py` - guarded benchmark persistence with atomic latest/history promotion
- `src/quantum_runtime/runtime/doctor.py` - guarded doctor persistence and structured workspace-safety propagation
- `src/quantum_runtime/workspace/baseline.py` - baseline set/clear helpers under the shared workspace lease
- `src/quantum_runtime/runtime/export.py` - current-workspace export validation against `specs/current.json` plus lease-guarded alias writes
- `src/quantum_runtime/runtime/pack.py` - staged pack directory assembly, guarded intent/plan backfill, and atomic event bundle writes
- `src/quantum_runtime/cli.py` - workspace-safety handling for compare, bench, doctor, baseline, export, and pack commands
- `src/quantum_runtime/workspace/__init__.py` - re-exported baseline persistence helpers
- `tests/test_cli_compare.py`, `tests/test_cli_bench.py`, `tests/test_cli_doctor.py`, `tests/test_cli_baseline.py`, `tests/test_cli_export.py`, `tests/test_cli_runtime_gap.py` - red/green CLI regressions for lock conflicts and interrupted-write recovery

## Decisions Made

- Kept compare, benchmark, and doctor computation outside the lease so the shared-workspace lock only covers final persistence.
- Treated `workspace_current` export as a current-alias contract, not a history-only replay contract, so latest report metadata is preserved while current qspec tampering still fails with the report hash mismatch.
- Used report-backed reconstruction for pack backfills because revision import integrity checks are stricter than the backfill use case and would otherwise block recovery of missing `intent/history` and `plans/history` artifacts.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Prevented report canonicalization from overwriting freshly written history artifacts with stale current aliases**
- **Found during:** Task 2
- **Issue:** After Plan 03, `write_report()` could still copy the previous current aliases back into a new revision's history paths before current/latest promotion, which made compare/export see phantom semantic drift.
- **Fix:** Updated report canonicalization to leave existing canonical history artifacts untouched.
- **Files modified:** `src/quantum_runtime/reporters/writer.py`
- **Verification:** `PYTHONPATH=src ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_export.py tests/test_cli_runtime_gap.py -q`
- **Committed in:** `8c9c385`

**2. [Rule 3 - Blocking] Reworked pack backfills to reconstruct from the revision report instead of the stricter revision resolver**
- **Found during:** Task 3
- **Issue:** When `intents/history/<revision>.json` was missing, the existing revision resolver failed on manifest integrity before pack could synthesize the missing history file, preventing recovery.
- **Fix:** Switched pack backfills to rebuild intent and plan objects from `reports/history/<revision>.json` and guard pending temp files before writing them back.
- **Files modified:** `src/quantum_runtime/runtime/pack.py`
- **Verification:** `PYTHONPATH=src ./.venv/bin/python -m pytest tests/test_cli_runtime_gap.py -q`
- **Committed in:** `8c9c385`

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both deviations were required to make the new workspace-safety contract trustworthy across existing runtime semantics. No extra product scope was added.

## Issues Encountered

- `export` and `pack` originally surfaced raw `WorkspaceLockConflict` exits because they could touch `WorkspaceManager.load_or_init()` before their new guarded mutation paths ran. The CLI and runtime entrypoints were tightened so those lock conflicts now flow through the same structured workspace-safety contract as the rest of the runtime.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Every mutating runtime command in the current local control plane now either writes safely or fails with a machine-readable conflict/recovery signal.
- Phase 3 now has one consistent workspace-safety story across exec and non-exec mutation paths.
- Remaining follow-up: phase-level verification and state/roadmap closeout.

## Self-Check: PASSED

- Verified command passes: `PYTHONPATH=src ./.venv/bin/python -m pytest tests/test_cli_compare.py tests/test_cli_bench.py tests/test_cli_doctor.py tests/test_cli_baseline.py tests/test_cli_export.py tests/test_cli_runtime_gap.py -q`
- Verified commits exist: `cfb1e9a`, `8c9c385`

---
*Phase: 03-concurrent-workspace-safety*
*Completed: 2026-04-12*
