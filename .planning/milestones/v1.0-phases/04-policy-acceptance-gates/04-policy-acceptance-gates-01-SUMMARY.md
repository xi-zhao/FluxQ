---
phase: 04-policy-acceptance-gates
plan: 01
subsystem: testing
tags: [ruff, mypy, pytest, bootstrap, docs]
requires:
  - phase: 03-concurrent-workspace-safety
    provides: existing Phase 4 smoke-test files and a stable local workspace baseline for policy-gate work
provides:
  - path-safe repo-local MyPy verification through `.venv/bin/python -m mypy`
  - contributor-facing Phase 4 Ruff/MyPy/pytest validation commands
  - a one-shot local validation entrypoint via `./scripts/dev-bootstrap.sh verify`
affects: [phase-04, local-verification, contributor-workflow]
tech-stack:
  added: []
  patterns: [module-form-mypy-invocation, explicit-phase-local-smoke-gate-docs]
key-files:
  created: [.planning/phases/04-policy-acceptance-gates/04-policy-acceptance-gates-01-SUMMARY.md]
  modified: [scripts/dev-bootstrap.sh, CONTRIBUTING.md]
key-decisions:
  - "Keep CI untouched and repair only the repo-local verification entrypoint for this plan."
  - "Run MyPy through the repo-local Python interpreter because the direct `.venv/bin/mypy` launcher is broken under the current workspace path."
patterns-established:
  - "Phase 4 local verification is documented as repo-local Ruff, `.venv/bin/python -m mypy`, then targeted pytest."
  - "`dev-bootstrap.sh verify` preflights a broken direct MyPy launcher and continues with the module-form invocation."
requirements-completed: []
duration: 8 min
completed: 2026-04-13
---

# Phase 04 Plan 01: Validation Gate Enablement Summary

**Path-safe local Phase 4 verification via repo-local Ruff, module-form MyPy, targeted pytest, and matching contributor guidance**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-12T23:35:00Z
- **Completed:** 2026-04-12T23:43:10Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Replaced the broken direct MyPy launcher in `scripts/dev-bootstrap.sh verify` with `"$ROOT_DIR/.venv/bin/python" -m mypy src`.
- Added a preflight note so the local bootstrap script makes the workspace-path launcher failure explicit instead of aborting on it.
- Documented the exact Phase 4 repo-local Ruff/MyPy/pytest command sequence in `CONTRIBUTING.md` and pointed contributors to `./scripts/dev-bootstrap.sh verify`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Make the repo-local verification gate path-safe for MyPy** - `695ed7a` (`fix`)
2. **Task 2: Document the exact Phase 4 validation commands** - `a2f14c5` (`chore`)

**Plan metadata:** Pending summary commit for this file only. `STATE.md` and `ROADMAP.md` were left untouched because the task ownership for this run was limited to the two repo files above plus this required summary artifact.

## Files Created/Modified

- `scripts/dev-bootstrap.sh` - switched local MyPy verification to module form and logged the broken-launcher fallback path
- `CONTRIBUTING.md` - added the exact Phase 4 repo-local Ruff/MyPy/pytest sequence plus `./scripts/dev-bootstrap.sh verify`
- `.planning/phases/04-policy-acceptance-gates/04-policy-acceptance-gates-01-SUMMARY.md` - recorded execution results, verification status, and follow-up context

## Decisions Made

- Kept the change local to the developer bootstrap path and did not alter CI workflow commands.
- Preserved the existing local gate order of qrun, Ruff, MyPy, and pytest; only the MyPy invocation path changed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The plan's required verification command is currently blocked by pre-existing Ruff failures outside the owned files:
  - `src/quantum_runtime/diagnostics/benchmark.py:381` (`F821 Undefined name 'Path'`)
  - `tests/test_runtime_workspace_safety.py:105` (`F841 Local variable 'original_write_diagrams' is assigned to but never used`)
- Those files were outside the allowed ownership for 04-01, so they were not modified in this run.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 4 now has one concrete repo-local validation contract for Ruff, MyPy, and the targeted policy-gate pytest smoke suite.
- Later Phase 4 plans can reference `./scripts/dev-bootstrap.sh verify` and the documented repo-local command sequence without re-deciding the broken MyPy launcher workaround.
- Full plan verification remains blocked until the unrelated Ruff errors above are fixed in their owning workstreams.

## Self-Check: PASSED

- Verified summary exists on disk: `.planning/phases/04-policy-acceptance-gates/04-policy-acceptance-gates-01-SUMMARY.md`
- Verified task commits exist: `695ed7a`, `a2f14c5`
