---
phase: 04-policy-acceptance-gates
plan: "04"
subsystem: runtime
tags: [doctor, policy, cli, ci, observability]
requires:
  - phase: 04-03
    provides: shared policy envelope helpers, verdict-first exit patterns, and policy-bearing JSONL completion payloads
provides:
  - `qrun doctor --ci` with explicit blocking and advisory findings
  - Additive doctor reports carrying policy, verdict, reason codes, next actions, and gate data
  - Verdict-driven doctor exit behavior that preserves legacy non-`--ci` behavior
affects: [policy-gates, observability, delivery-bundles, ci]
tech-stack:
  added: []
  patterns:
    - Project existing doctor `issues` and `advisories` into an additive CI policy layer instead of rewriting health classification
    - Exclude CI-only doctor fields from legacy JSON and persisted reports unless `--ci` is requested
key-files:
  created: []
  modified:
    - src/quantum_runtime/runtime/policy.py
    - src/quantum_runtime/runtime/doctor.py
    - src/quantum_runtime/cli.py
    - src/quantum_runtime/runtime/exit_codes.py
    - tests/test_cli_doctor.py
    - tests/test_cli_observability.py
    - tests/test_runtime_policy.py
key-decisions:
  - "Doctor CI reuses the existing `issues` versus `advisories` split and only projects it into explicit blocking/advisory fields."
  - "Doctor reports keep legacy raw findings intact; CI verdict, reason-code, and gate fields are additive and only emitted when `--ci` is requested."
  - "Doctor exit behavior is verdict-first only when a CI verdict exists; legacy workspace/dependency fallback mapping remains unchanged otherwise."
patterns-established:
  - "Doctor CI uses `DoctorPolicy(mode=\"ci\", block_on_issues=True)` to derive `blocking_issues`, `advisory_issues`, `verdict`, `reason_codes`, `next_actions`, and `gate`."
  - "CLI JSON and JSONL doctor output exclude CI-only fields for non-`--ci` runs by serializing with `exclude_none=True`."
requirements-completed: [POLC-03]
duration: 4min
completed: 2026-04-13
---

# Phase 4 Plan 04: Doctor CI Gate Summary

**Doctor CI gating with explicit blocking and advisory findings, additive policy envelopes, and verdict-driven exits**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-13T00:06:22Z
- **Completed:** 2026-04-13T00:10:09Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Added RED coverage for advisory-only and blocking `qrun doctor --ci` JSON flows, CI JSONL completion payloads, and direct doctor-policy projection.
- Extended the runtime doctor report shape with additive CI policy fields and introduced `DoctorPolicy` plus `apply_doctor_policy()` in the shared policy module.
- Wired `qrun doctor --ci` through the CLI and exit-code mapper so blocking findings return exit code `2` while non-`--ci` doctor behavior stays backward compatible.

## Task Commits

1. **Task 1: Add failing doctor CI regressions** - `94ead7e` (`test`)
2. **Task 2: Project doctor findings into the shared policy envelope** - `6281de7` (`feat`)
3. **Task 3: Wire `doctor --ci` and verdict-based exit behavior** - `45a2845` (`feat`)

## Files Created/Modified

- `src/quantum_runtime/runtime/policy.py` - Adds `DoctorPolicy`, doctor reason-code slugging, next-action selection, and the shared doctor policy evaluator.
- `src/quantum_runtime/runtime/doctor.py` - Extends `DoctorReport`, adds `ci` support to `run_doctor()`, and persists CI-enriched reports without changing legacy serialization.
- `src/quantum_runtime/cli.py` - Adds the `--ci` doctor flag, threads CI mode into `run_doctor()`, and keeps legacy JSON/JSONL output clean by excluding absent CI fields.
- `src/quantum_runtime/runtime/exit_codes.py` - Makes doctor exits verdict-first when a CI verdict exists.
- `tests/test_cli_doctor.py` - Covers advisory-only pass, blocking failure, and preserved non-`--ci` doctor behavior.
- `tests/test_cli_observability.py` - Pins the final `doctor_completed` JSONL payload to include the doctor policy envelope.
- `tests/test_runtime_policy.py` - Verifies `apply_doctor_policy()` maps raw findings into blocking/advisory CI fields and reason codes.

## Decisions Made

- Kept the existing doctor health classifier as the source of truth and layered CI semantics on top of it instead of redefining backend optionality or workspace integrity rules.
- Used deterministic slugged reason codes (`doctor_blocking_issue:*`, `doctor_advisory_issue:*`) so machine consumers can compare doctor verdicts without parsing free-form strings.
- Preserved legacy doctor callers by only surfacing CI fields and verdict-driven exits when `--ci` is explicitly requested.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pulled minimal CLI and exit-code wiring forward so Task 2 verification could pass**
- **Found during:** Task 2 verification
- **Issue:** The plan's Task 2 verify command includes `tests/test_cli_doctor.py`, and the new RED coverage exercised `qrun doctor --ci` before the CLI flag and verdict-based exit mapping existed.
- **Fix:** Added the minimal `--ci` CLI threading and verdict-first doctor exit handling before rerunning the Task 2 verify command, then committed the CLI files separately in Task 3.
- **Files modified:** `src/quantum_runtime/cli.py`, `src/quantum_runtime/runtime/exit_codes.py`
- **Verification:** `./.venv/bin/python -m pytest tests/test_runtime_policy.py tests/test_cli_doctor.py -q --maxfail=1`
- **Committed in:** `45a2845`

**2. [Rule 1 - Bug] Removed an environment-specific assumption from the new doctor JSONL observability test**
- **Found during:** Task 3 verification
- **Issue:** The new blocking doctor JSONL test assumed `advisory_issues == []`, but optional backend advisories can still coexist with a blocking workspace finding on this machine.
- **Fix:** Relaxed the assertion to require the `advisory_issues` field to exist as a list, which matches the plan contract without depending on local optional-backend availability.
- **Files modified:** `tests/test_cli_observability.py`
- **Verification:** `./.venv/bin/python -m pytest tests/test_cli_doctor.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1`
- **Committed in:** `45a2845`

---

**Total deviations:** 2 auto-fixed (1 blocking issue, 1 bug)
**Impact on plan:** Both fixes were necessary to make the planned verification commands and observability assertions correct. No scope creep.

## Issues Encountered

- Task 2's stated verification command implicitly depended on part of the Task 3 CLI surface once the RED tests covered `doctor --ci`, so the sequencing had to be tightened during execution.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 4 now has compare, benchmark, and doctor policy surfaces with a shared verdict/gate vocabulary.
- Phase 5 delivery work can consume doctor reports as CI-native acceptance artifacts without custom wrapper logic.

## Self-Check: PASSED

- Verified summary file exists at `.planning/phases/04-policy-acceptance-gates/04-policy-acceptance-gates-04-SUMMARY.md`
- Verified task commits exist: `94ead7e`, `6281de7`, `45a2845`
