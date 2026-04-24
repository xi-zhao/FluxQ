---
phase: 09-ibm-access-backend-readiness
plan: "02"
subsystem: auth
tags: [ibm, doctor, observability, policy, ci]
requires:
  - phase: 09-01
    provides: IBM access profile persistence, `resolve_ibm_access()`, and the `build_ibm_service()` seam
provides:
  - IBM opt-in doctor gating that fail-closes `doctor --ci` on unresolved IBM auth/profile readiness
  - Shared IBM reason-code projection into doctor policy, JSON output, and JSONL completion events
  - Stable IBM remediation and next-action vocabulary for CI and agent consumers
affects: [backend-readiness, remote-readiness, observability, ci]
tech-stack:
  added: []
  patterns:
    - Explicit `[remote.ibm]` opt-in is the only trigger for IBM doctor checks; local-only workspaces skip IBM gating entirely
    - Doctor policy preserves provider-specific reason codes instead of flattening IBM findings into generic doctor slugs
    - Doctor JSON and JSONL share the same IBM reason-code, next-action, and gate vocabulary
key-files:
  created: []
  modified:
    - src/quantum_runtime/runtime/doctor.py
    - src/quantum_runtime/runtime/policy.py
    - src/quantum_runtime/runtime/contracts.py
    - src/quantum_runtime/runtime/observability.py
    - tests/test_cli_doctor.py
    - tests/test_cli_observability.py
key-decisions:
  - "IBM doctor checks only run when `qrun.toml` explicitly contains `[remote.ibm]`, so local-only workspaces keep existing doctor semantics."
  - "IBM doctor findings keep their provider-specific reason codes through `apply_doctor_policy()`, and shared observability maps those codes to stable next actions."
patterns-established:
  - "Doctor CI adds IBM auth/profile findings as regular doctor issues while attaching IBM reason codes only for CI policy projection."
  - "Plan-level smoke selectors can rely on `-k 'ibm_doctor'` without changing task-level exact test names."
requirements-completed: [AUTH-01]
duration: 6min
completed: 2026-04-18
---

# Phase 09 Plan 02: IBM Doctor Readiness Summary

**IBM opt-in doctor gating with preserved provider reason codes, shared JSON/JSONL observability, and fail-closed CI readiness checks**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-18T05:54:58Z
- **Completed:** 2026-04-18T06:01:12Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added IBM auth/profile gating to `qrun doctor --ci` that only activates for explicit `[remote.ibm]` workspaces and blocks unresolved remote access readiness.
- Preserved IBM-specific reason codes through doctor policy projection so CI payloads keep provider-level signals instead of only generic doctor slugs.
- Unified IBM remediation and next-action vocabulary across doctor JSON and JSONL completion payloads, while proving secret values are not echoed.

## Task Commits

Each task was committed atomically through TDD:

1. **Task 1: 把 IBM auth/profile 失败态接入 `doctor --ci`** - `a7e5803` (`test`), `acd04af` (`feat`)
2. **Task 2: 统一 IBM doctor 的 remediation 与 JSONL observability** - `f3b119e` (`test`), `d7d79ad` (`feat`), `bc536ef` (`refactor`)

## Files Created/Modified

- `src/quantum_runtime/runtime/doctor.py` - Adds opt-in IBM doctor finding generation, stable IBM issue messages, and fail-closed mapping through the existing doctor report.
- `src/quantum_runtime/runtime/policy.py` - Merges pre-attached IBM reason codes into doctor policy projection and derives next actions from the preserved reason-code set.
- `src/quantum_runtime/runtime/contracts.py` - Adds stable remediation strings for IBM doctor reason codes.
- `src/quantum_runtime/runtime/observability.py` - Maps IBM doctor reason codes to shared next actions used by both JSON and JSONL payloads.
- `tests/test_cli_doctor.py` - Covers IBM token-env blocking, opt-in skipping, and missing IBM runtime dependency behavior.
- `tests/test_cli_observability.py` - Verifies IBM doctor JSON/JSONL parity, secret redaction, and plan-level `ibm_doctor` smoke selection.

## Decisions Made

- Reused `resolve_ibm_access()` plus `build_ibm_service()` as the only IBM doctor seam, instead of adding parallel IBM-specific health plumbing.
- Kept IBM findings additive to the existing doctor issue model so legacy local doctor flows stay intact while CI gets fail-closed remote readiness semantics.
- Used shared reason-code-to-action mapping in `observability.py` as the single source of truth for IBM doctor next actions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `ibm_doctor`-keyed observability aliases so the plan smoke command selects the new tests**
- **Found during:** Task 2 verification
- **Issue:** The plan-level verification command uses `pytest -k 'ibm_doctor'`, but the new exact-name observability regressions did not include that selector.
- **Fix:** Added alias test entry points in `tests/test_cli_observability.py` that reuse the exact regression bodies while matching the plan-level smoke selector.
- **Files modified:** `tests/test_cli_observability.py`
- **Verification:** `uv run pytest tests/test_cli_observability.py -k 'ibm_doctor' -q --maxfail=1`
- **Committed in:** `bc536ef`

---

**Total deviations:** 1 auto-fixed (1 blocking issue)
**Impact on plan:** The fix only aligned test discovery with the authored verification command. No scope creep.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 09 now has a canonical IBM doctor gate that can fail closed before backend discovery or submit work begins.
- Plan 03 can project IBM backend readiness on top of the same `resolve_ibm_access()` and `build_ibm_service()` seams without redefining doctor vocabulary.

## Self-Check: PASSED

- Verified summary file exists at `.planning/phases/09-ibm-access-backend-readiness/09-02-SUMMARY.md`
- Verified task commits exist: `a7e5803`, `acd04af`, `f3b119e`, `d7d79ad`, `bc536ef`
