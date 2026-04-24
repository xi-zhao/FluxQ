---
phase: 09-ibm-access-backend-readiness
plan: "03"
subsystem: api
tags: [ibm, backend-list, readiness, cli, qiskit]
requires:
  - phase: 09-01
    provides: IBM access profile persistence, `resolve_ibm_access()`, and the `build_ibm_service()` seam
provides:
  - Workspace-aware `qrun backend list --json --workspace <path>` output with IBM provider context
  - IBM target readiness projection with per-target `operational`, `status_msg`, `pending_jobs`, `num_qubits`, and `backend_version`
  - Blocked-but-readable IBM remote readiness payloads without automatic backend selection
affects: [remote-submit, backend-selection, observability, provider-readiness]
tech-stack:
  added: []
  patterns:
    - `backend list` remains the single IBM discovery surface, extended additively through a top-level `remote` block
    - IBM backend discovery flows only through `resolve_ibm_access()` and the exported `build_ibm_service()` seam, never by importing the IBM SDK directly in `backend_list.py`
    - Remote readiness is explicit and readable, while `remote_submit` stays false and no recommendation fields are emitted
key-files:
  created: []
  modified:
    - src/quantum_runtime/cli.py
    - src/quantum_runtime/runtime/backend_registry.py
    - src/quantum_runtime/runtime/backend_list.py
    - tests/test_cli_backend_list.py
key-decisions:
  - "Kept `qrun backend list` as the only IBM inventory surface and extended it with an additive `remote` block instead of forking a provider-specific command."
  - "Projected IBM provider and target readiness only through `resolve_ibm_access()` plus `build_ibm_service()`, so backend discovery reuses the Phase 09 IBM access seam."
  - "Explicitly withheld backend recommendation and submit capability: `ibm-runtime` advertises `remote_readiness=True`, `remote_submit=False`, and the JSON payload omits `recommended_backend`, `selected_backend`, and `least_busy`."
patterns-established:
  - "Backend list payloads surface provider-level readiness and target-level readiness separately, so submit planning can consume explicit evidence instead of a hidden scheduler pick."
  - "IBM SDK/auth/service failures degrade into stable reason-coded payloads rather than CLI crashes."
requirements-completed: [BACK-01]
duration: 6min
completed: 2026-04-18
---

# Phase 09 Plan 03: IBM Backend Readiness Summary

**Workspace-aware IBM backend inventory with additive remote readiness payloads, target-level readiness projection, and blocked fallbacks that never auto-select a backend**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-18T06:06:20Z
- **Completed:** 2026-04-18T06:11:56Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `--workspace` to `qrun backend list` and threaded the workspace root into runtime backend discovery so IBM profile context comes from the selected workspace.
- Published an `ibm-runtime` backend descriptor plus an additive top-level `remote` block that exposes IBM provider readiness without claiming submit support.
- Projected IBM targets through `build_ibm_service()` into stable readiness JSON and returned blocked payloads with reason codes when IBM auth, SDK, or service setup failed.

## Task Commits

Each task was committed atomically through TDD:

1. **Task 1: 让 `backend list` 具备 workspace-aware IBM inventory surface** - `2659294` (`test`), `241fba3` (`feat`)
2. **Task 2: 投影 IBM target-level readiness，而不做自动 backend 选择** - `dc37be1` (`test`), `0daf64e` (`feat`), `f6749fa` (`fix`)

## Files Created/Modified

- `src/quantum_runtime/cli.py` - Adds `backend list --workspace` and passes the selected workspace root into runtime discovery.
- `src/quantum_runtime/runtime/backend_registry.py` - Publishes the readiness-only `ibm-runtime` backend descriptor with `remote_readiness=True` and `remote_submit=False`.
- `src/quantum_runtime/runtime/backend_list.py` - Builds the additive IBM `remote` summary, enumerates targets through `build_ibm_service()`, and degrades to blocked readiness payloads instead of raising.
- `tests/test_cli_backend_list.py` - Covers workspace-aware CLI wiring, the `ibm-runtime` descriptor, no-auto-select guarantees, target readiness projection, and blocked IBM-service fallbacks.

## Decisions Made

- Reused the Phase 09 IBM access seam instead of introducing a second IBM discovery path.
- Split provider readiness (`remote.readiness`) from target readiness (`remote.targets[*].readiness`) so later submit work can consume both levels explicitly.
- Preserved FluxQ's explicit-selection rule by omitting all recommendation fields and keeping `remote_submit` false.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Tightened `backend_list.py` typing after plan-level verification exposed mypy failures**
- **Found during:** Overall verification
- **Issue:** `mypy` flagged an optional `ibm-runtime` descriptor read and the `object`-typed IBM service seam at target enumeration time.
- **Fix:** Guarded the optional descriptor lookup before reading `available` and cast the seam object only at the `backends()` boundary.
- **Files modified:** `src/quantum_runtime/runtime/backend_list.py`
- **Verification:** `uv run python -m mypy src` and `uv run pytest tests/test_cli_backend_list.py -q --maxfail=1`
- **Committed in:** `f6749fa`

---

**Total deviations:** 1 auto-fixed (1 blocking issue)
**Impact on plan:** The fix only tightened type-safety around the planned backend list seam. No scope creep.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Remote submit work can now consume explicit IBM provider context, target readiness, and blocked reason codes from one stable backend-list contract.
- The plan preserved the product rule that backend choice stays explicit: inventory is readable, but FluxQ still does not auto-pick or silently submit to an IBM backend.

## Self-Check: PASSED

- Verified summary file exists at `.planning/phases/09-ibm-access-backend-readiness/09-03-SUMMARY.md`
- Verified task commits exist: `2659294`, `241fba3`, `dc37be1`, `0daf64e`, `f6749fa`
