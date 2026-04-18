---
phase: 04-policy-acceptance-gates
plan: 02
subsystem: infra
tags: [compare, policy, baseline, cli, pytest]
requires:
  - phase: 03-concurrent-workspace-safety
    provides: lock-scoped compare persistence and non-exec writer safety for workspace mutations
provides:
  - baseline/current compare fail-on regression coverage for POLC-01
  - schema-versioned compare latest/history persistence on new writes
  - explicit CLI delegation through compare_workspace_baseline for baseline mode
affects: [compare, policy, baseline, cli]
tech-stack:
  added: []
  patterns: [schema-versioned compare persistence, baseline compare runtime helper delegation]
key-files:
  created: []
  modified: [src/quantum_runtime/runtime/compare.py, src/quantum_runtime/cli.py, tests/test_cli_compare.py, tests/test_cli_runtime_gap.py]
key-decisions:
  - "Keep compare policy activation explicit through CLI flags; baseline mode delegates through compare_workspace_baseline instead of consuming runtime policy hints."
  - "Persist compare latest/history artifacts through ensure_schema_payload() on new writes without rewriting prior history files."
patterns-established:
  - "Compare latest/history writers serialize the same schema-versioned payload shape that the CLI emits."
  - "Baseline compare mode in cli.py delegates to the runtime helper while preserving explicit event emission and exit-code handling."
requirements-completed: [POLC-01]
duration: 1 min
completed: 2026-04-13
---

# Phase 04 Plan 02: Baseline Compare Gate Summary

**Baseline/current compare fail-on coverage with schema-versioned persisted artifacts and explicit CLI delegation through the shared compare helper**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-12T23:47:08Z
- **Completed:** 2026-04-12T23:48:19Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added a baseline/current regression that drives the public CLI through `exec -> baseline set -> exec -> compare --baseline --fail-on subject_drift --json` and pins `verdict`, `gate`, exit code `2`, and the populated `baseline` block.
- Hardened compare persistence so `.quantum/compare/latest.json` and `.quantum/compare/history/*.json` now include `schema_version` on new writes.
- Removed the inline baseline compare flow from `cli.py` so baseline mode explicitly delegates through `compare_workspace_baseline(...)` while preserving existing flag validation and exit behavior.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add failing baseline/current compare regressions** - `571e246` (`test`)
2. **Task 2: Route baseline compare through one helper and persist schema-versioned compare artifacts** - `4a3d6b0` (`feat`)

**Plan metadata:** Summary/state/roadmap closeout committed separately after this summary is written.

## Files Created/Modified

- `src/quantum_runtime/runtime/compare.py` - schema-versioned compare latest/history serialization via `ensure_schema_payload()`
- `src/quantum_runtime/cli.py` - baseline compare mode delegates through `compare_workspace_baseline(...)`
- `tests/test_cli_compare.py` - baseline/current fail-on regression plus persisted compare artifact schema assertions
- `tests/test_cli_runtime_gap.py` - tightened explicit left/right compare fail-on regression to assert policy ownership

## Decisions Made

- Kept compare policy activation CLI-flag driven for this phase; no `QSpec.runtime.policy_hints` auto-activation was added.
- Applied schema hardening only to new compare writes so existing history artifacts remain untouched.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The plan verification command still fails at `python -m mypy src` because of pre-existing errors in `src/quantum_runtime/runtime/contracts.py`, `src/quantum_runtime/runtime/run_manifest.py`, `src/quantum_runtime/runtime/control_plane.py`, and `src/quantum_runtime/runtime/pack.py`. These files are outside this plan's ownership and match the existing Phase 4 state blocker about repo-wide MyPy noise.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `qrun compare --baseline --fail-on ... --json` now has explicit plan ownership, regression coverage, and schema-versioned persisted evidence for downstream policy composition.
- Benchmark and doctor policy work can now trust compare latest/history artifacts to match the CLI JSON contract on new writes.
- Remaining repo-level concern: `mypy src` is still red outside this plan's files and may obscure unrelated regressions until Phase 4 validation debt is addressed.

## Self-Check: PASSED

- Verified summary file exists: `.planning/phases/04-policy-acceptance-gates/04-policy-acceptance-gates-02-SUMMARY.md`
- Verified task commits exist: `571e246`, `4a3d6b0`

---
*Phase: 04-policy-acceptance-gates*
*Completed: 2026-04-13*
