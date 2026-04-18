---
phase: 04-policy-acceptance-gates
plan: "03"
subsystem: runtime
tags: [benchmark, policy, cli, qiskit, typer]
requires:
  - phase: 04-02
    provides: compare-style policy vocabulary, baseline resolution flow, and schema-versioned persisted gate artifacts
provides:
  - Benchmark policy primitives with verdict, reason-code, and gate envelopes
  - Baseline-backed `qrun bench` acceptance gating with explicit CLI policy flags
  - Provenance-safe benchmark persistence keyed to the evaluated source revision
affects: [policy-gates, doctor-ci, delivery-bundles, observability]
tech-stack:
  added: []
  patterns:
    - Separate benchmark computation from persistence so policy metadata can be attached before workspace writes
    - Keep benchmark policy activation explicit through CLI flags and saved baseline evidence
key-files:
  created:
    - src/quantum_runtime/runtime/policy.py
    - tests/test_runtime_policy.py
  modified:
    - src/quantum_runtime/diagnostics/benchmark.py
    - src/quantum_runtime/cli.py
    - src/quantum_runtime/runtime/exit_codes.py
    - src/quantum_runtime/runtime/contracts.py
    - tests/test_cli_bench.py
    - tests/test_cli_observability.py
key-decisions:
  - "Benchmark policy remains CLI-flag driven in Phase 4; the implementation does not auto-consume `QSpec.runtime.policy_hints`."
  - "Benchmark history now keys off `source_revision` and carries `source_kind` so imported report/revision benchmark runs cannot masquerade as the mutable current revision."
  - "When benchmark policy is requested, CLI exit behavior becomes verdict-first; legacy raw-status exit mapping remains the fallback for non-policy runs."
patterns-established:
  - "BenchmarkReport is an additive policy carrier with `baseline`, `comparison`, `policy`, `verdict`, `reason_codes`, `next_actions`, and `gate`."
  - "Saved benchmark baseline evidence is loaded explicitly from `.quantum/benchmarks/history/<revision>.json` and missing evidence fails closed with `baseline_benchmark_missing`."
requirements-completed: [POLC-02]
duration: 6min
completed: 2026-04-13
---

# Phase 4 Plan 03: Benchmark Baseline Policy Gate Summary

**Baseline-backed benchmark policy gating with provenance-safe history persistence and verdict-driven CLI exits**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-12T23:55:00Z
- **Completed:** 2026-04-13T00:00:56Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Added a shared benchmark policy layer in `src/quantum_runtime/runtime/policy.py` that evaluates subject parity, backend presence, comparability, status regressions, and metric regression thresholds in a fail-closed order.
- Extended benchmark reports to carry source provenance plus additive policy metadata, and changed benchmark persistence to write history under the evaluated `source_revision`.
- Wired `qrun bench` to load saved baseline benchmark evidence, emit policy-bearing JSON/JSONL payloads, and return exit code `2` on policy failure without changing legacy non-policy behavior.

## Task Commits

1. **Task 1: Add failing benchmark policy regressions** - `6ff5480` (`test`)
2. **Task 2: Add shared benchmark policy primitives and provenance-aware benchmark reports** - `e991104` (`feat`)
3. **Task 3: Wire benchmark baseline flags, error contracts, and verdict-driven exits** - `43c0153` (`feat`)
4. **Verification auto-fix: harden benchmark baseline error handling** - `16ebc89` (`fix`)

## Files Created/Modified

- `src/quantum_runtime/runtime/policy.py` - Shared `BenchmarkPolicy`, `PolicyVerdict`, and `apply_benchmark_policy()` evaluator.
- `src/quantum_runtime/diagnostics/benchmark.py` - Adds source provenance and policy envelope fields to `BenchmarkReport`, plus provenance-safe benchmark persistence.
- `src/quantum_runtime/cli.py` - Adds explicit benchmark gating flags, baseline benchmark loading, post-policy persistence, and JSON/JSONL benchmark gate output.
- `src/quantum_runtime/runtime/exit_codes.py` - Makes benchmark exits verdict-first when policy is requested.
- `src/quantum_runtime/runtime/contracts.py` - Adds remediations for `baseline_benchmark_missing` and `invalid_benchmark_policy`.
- `tests/test_cli_bench.py` - Covers saved-baseline benchmark loading, imported revision/report provenance persistence, and baseline gate failure paths.
- `tests/test_cli_observability.py` - Pins benchmark JSONL completion payloads to include policy-bearing fields when gating is requested.
- `tests/test_runtime_policy.py` - Direct unit coverage for subject mismatch and metric regression policy failures.

## Decisions Made

- Kept benchmark policy activation explicit through `qrun bench` flags in this phase instead of inferring policy from runtime hints.
- Treated saved benchmark evidence as a first-class workspace artifact, loaded directly from benchmark history rather than recomputing baseline metrics on demand.
- Preserved backward compatibility for legacy benchmark callers by only changing exit semantics when a policy verdict exists.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed a diagnostics/runtime circular import introduced by schema-versioned benchmark persistence**
- **Found during:** Task 2 verification
- **Issue:** Importing `runtime.contracts` from `diagnostics.benchmark` caused package initialization to recurse through `runtime.__init__` and `diagnostics.__init__`.
- **Fix:** Kept benchmark persistence schema handling local to `benchmark.py` by serializing `BenchmarkReport.model_dump(...)` and setting `schema_version` directly.
- **Files modified:** `src/quantum_runtime/diagnostics/benchmark.py`
- **Verification:** `./.venv/bin/python -m pytest tests/test_cli_bench.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1`
- **Committed in:** `e991104`

**2. [Rule 1 - Bug] Hardened the missing baseline benchmark error path for MyPy**
- **Found during:** Plan-level verification
- **Issue:** MyPy could not prove `baseline_resolution` was non-null inside the `FileNotFoundError` branch.
- **Fix:** Added a guarded `missing_revision` fallback before formatting the human-readable error.
- **Files modified:** `src/quantum_runtime/cli.py`
- **Verification:** `./.venv/bin/ruff check src tests && ./.venv/bin/python -m mypy src && ./.venv/bin/python -m pytest tests/test_cli_bench.py tests/test_cli_observability.py tests/test_runtime_policy.py -q --maxfail=1`
- **Committed in:** `16ebc89`

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes were required for correctness and verification. No scope creep.

## Issues Encountered

- Existing imported-report benchmark persistence tests assumed report-file benchmarks never wrote history. The plan’s provenance requirement made that behavior ambiguous, so the test contract was updated to require history writes keyed to the imported source revision.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 04 now has compare and benchmark policy surfaces with consistent verdict/gate semantics, which reduces Phase 04-04 work to the doctor path.
- Phase 05 delivery work can rely on benchmark history carrying the true evaluated revision for imported report/revision inputs.

## Self-Check: PASSED

- Verified summary file exists at `.planning/phases/04-policy-acceptance-gates/04-policy-acceptance-gates-03-SUMMARY.md`
- Verified task commits exist: `6ff5480`, `e991104`, `43c0153`, `16ebc89`
