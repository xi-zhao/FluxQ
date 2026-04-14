---
status: testing
phase: 04-policy-acceptance-gates
source:
  - 04-policy-acceptance-gates-01-SUMMARY.md
  - 04-policy-acceptance-gates-02-SUMMARY.md
  - 04-policy-acceptance-gates-03-SUMMARY.md
  - 04-policy-acceptance-gates-04-SUMMARY.md
started: 2026-04-14T12:13:56Z
updated: 2026-04-14T12:26:21Z
---

## Current Test

[testing complete]

## Tests

### 1. Phase 4 Local Verify Path
expected: Running the documented Phase 4 local verification flow should complete Ruff, module-form MyPy, and the policy-gate pytest suite without unrelated test failures. The one-shot entrypoint should match the documented phase-specific gate rather than drifting to a broader repo test run.
result: pass

### 2. Baseline Compare Policy Gate
expected: After establishing a baseline revision and changing the subject workload, `qrun compare --baseline --fail-on subject_drift --json` should fail closed with exit code `2`, return `verdict: fail`, list `subject_drift` in `failed_checks`, and include populated baseline metadata.
result: pass

### 3. Benchmark Baseline Policy Gate
expected: When benchmark policy is requested against saved baseline evidence, `qrun bench ... --json` should include policy and gate fields, preserve the evaluated source revision in persisted history, and return exit code `2` for a forbidden regression while leaving legacy non-policy behavior unchanged.
result: pass

### 4. Doctor CI Policy Gate
expected: Running `qrun doctor --ci --json` on a workspace with blocking issues should return explicit `blocking_issues` and `advisory_issues`, emit a fail verdict with gate metadata, and exit code `2`, while non-`--ci` doctor behavior remains backward compatible.
result: pass

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
