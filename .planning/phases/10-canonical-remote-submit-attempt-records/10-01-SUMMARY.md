---
phase: 10-canonical-remote-submit-attempt-records
plan: "01"
subsystem: runtime
tags: [python, qiskit, pydantic, workspace, remote-submit, ibm]
requires: []
provides:
  - remote attempt identity separate from workspace revision identity
  - atomic `.quantum/remote/...` attempt persistence and latest alias promotion
  - typed remote-attempt runtime seam for later IBM submit and reopen flows
affects: [10-02, 10-03, remote-submit, workspace]
tech-stack:
  added: []
  patterns:
    - additive workspace counters for non-revision identities
    - atomic history plus latest-alias writes for remote attempt records
    - resolved-input snapshots reused for submit-time provenance
key-files:
  created:
    - src/quantum_runtime/runtime/remote_attempts.py
    - tests/test_runtime_remote_attempts.py
  modified:
    - src/quantum_runtime/runtime/__init__.py
    - src/quantum_runtime/workspace/manager.py
    - src/quantum_runtime/workspace/manifest.py
    - src/quantum_runtime/workspace/paths.py
key-decisions:
  - "Keep `current_attempt` additive and separate from `current_revision` so remote submit never impersonates a finalized local run."
  - "Persist submit-time snapshots only under `.quantum/remote/...` and leave report/manifest aliases untouched until later finalization phases."
  - "Build remote attempt records from `ResolvedRuntimeInput` and execution-plan snapshots to preserve canonical ingress provenance."
patterns-established:
  - "Remote attempt persistence uses workspace locks plus atomic history/latest writes."
  - "Remote attempt records store non-secret provider metadata and reject token-bearing extras."
requirements-completed: [REMT-01, REMT-02]
duration: 7min
completed: 2026-04-18
---

# Phase 10 Plan 01: Remote Attempt Store Summary

**Remote attempt IDs, atomic `.quantum/remote` persistence, and typed submit-time provenance records for later IBM submit flows**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-18T14:35:00Z
- **Completed:** 2026-04-18T14:42:10Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added a dedicated `attempt_000001` identity path in `WorkspaceManifest` and `WorkspaceHandle` without changing revision numbering semantics.
- Seeded the remote workspace skeleton under `.quantum/remote/attempts`, `.quantum/remote/artifacts`, `.quantum/remote/events`, and `.quantum/remote/trace`.
- Implemented typed remote-attempt records plus atomic snapshot persistence for `qspec.json`, `intent.json`, `plan.json`, `submit_payload.json`, and the authoritative latest/history attempt records.
- Added regression coverage proving remote submit persistence does not create finalized report/manifest aliases or bump `current_revision`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add remote-attempt identity and workspace path scaffolding** - `17dcbf1` (`feat`)
2. **Task 2: Persist canonical remote-attempt records and snapshots atomically** - `0cfa351` (`feat`)

**Additional auto-fix:** `9cf2b2a` (`fix`) for post-task verification cleanup

## Files Created/Modified

- `src/quantum_runtime/workspace/paths.py` - adds remote attempt, artifact, event, and trace directory helpers plus required skeleton creation.
- `src/quantum_runtime/workspace/manifest.py` - adds additive `current_attempt` state with `next_attempt()` and `bump_attempt()`.
- `src/quantum_runtime/workspace/manager.py` - adds lock-safe `reserve_attempt()` on `WorkspaceHandle`.
- `src/quantum_runtime/runtime/remote_attempts.py` - defines typed remote-attempt models, atomic persistence helpers, latest-alias guard, and load helpers.
- `src/quantum_runtime/runtime/__init__.py` - re-exports the remote-attempt seam from the runtime barrel.
- `tests/test_runtime_remote_attempts.py` - covers attempt sequencing, remote directory scaffolding, secret rejection, atomic persistence, no-revision-bump behavior, and load semantics.

## Decisions Made

- Remote attempts are tracked with a distinct `current_attempt` field rather than overloading `current_revision`.
- Submit-time persistence is isolated to `.quantum/remote/...`; finalized run aliases remain the responsibility of later phases.
- Remote attempt records are schema-versioned and intentionally limited to non-secret provider references such as `auth_source`, backend coordinates, and job ID.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Corrected nested remote-attempt model construction for MyPy**
- **Found during:** Plan-level verification after Task 2
- **Issue:** `RemoteAttemptRecord` was instantiated with raw nested dictionaries, which left `uv run python -m mypy src` failing on argument types.
- **Fix:** Replaced the raw dictionaries with explicit `RemoteAttemptInput` and `RemoteAttemptQspec` instances inside `persist_remote_attempt()`.
- **Files modified:** `src/quantum_runtime/runtime/remote_attempts.py`
- **Verification:** `uv run pytest tests/test_runtime_remote_attempts.py -q --maxfail=1`; `uv run python -m mypy src`
- **Committed in:** `9cf2b2a`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The fix stayed inside the planned seam and was required to satisfy the plan's verification gate. No scope change.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 10-02 can build the IBM submit adapter directly on top of the new `remote_attempts` seam.
- Phase 10-03 can wire CLI submit flows to the same persistence helpers without revisiting workspace path or identity design.
- No blockers remain for the attempt-store foundation.

## Self-Check: PASSED

- Verified summary file exists at `.planning/phases/10-canonical-remote-submit-attempt-records/10-01-SUMMARY.md`.
- Verified task and verification-fix commits exist: `17dcbf1`, `0cfa351`, `9cf2b2a`.

---
*Phase: 10-canonical-remote-submit-attempt-records*
*Completed: 2026-04-18*
